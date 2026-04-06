import click
import os
import json
import re
import sys
from . import __version__
from .ci.jenkins import JenkinsClient
from .repo.gerrit import GerritClient
from .common.settings import settings, ENV_VAR_LIST, IS_DRY_RUN
from .common.utils import info_color, print_banner, load_json_file
from requests.auth import HTTPBasicAuth
from .trigger import should_trigger_pipeline, trigger_jenkins_job

# --- 全局常量定义 ---
CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
GLOBAL_CONFIG_PATH = os.path.join(CURRENT_FILE_DIR, "conf", "conf_global.json")
DEFAULT_TRIGGER_CONFIG = os.path.join(CURRENT_FILE_DIR, "conf", "trigger_config.json")

class Context:
    def __init__(self):
        self.jenkins = JenkinsClient()
        self.gerrit = GerritClient()

@click.group()
@click.version_option(version=__version__, prog_name="dci")
@click.pass_context
def cli(ctx):
    """DCI (Distributed CI) - Gerrit + Jenkins 自动化编排工具"""
    ctx.obj = Context()

@cli.command()
@click.pass_context
def info(ctx):
    """显示系统信息和 Banner"""
    print_banner()

@cli.command()
@click.option('--config', '-c', required=True, type=click.Path(exists=True), help='触发规则配置文件路径 (JSON)')
@click.option('--dry-run', is_flag=True, help='仅打印执行计划，不实际触发')
@click.pass_context
def trigger(ctx, config, dry_run):
    """主函数：解析配置，获取变更，匹配规则，触发下游任务"""
    dry_run = dry_run or IS_DRY_RUN
    info_color('info', "=== 开始 Gerrit CI 触发分析 ===")
    
    trigger_config = load_json_file(config, "触发规则配置")
    if not trigger_config:
        sys.exit(1)
        
    pipelines = trigger_config.get('pipelines', {})
    global_ignore = trigger_config.get('global_ignore', {}).get('paths', [])
    
    change_id = os.getenv("GERRIT_CHANGE_ID")
    patchset_num = os.getenv("GERRIT_PATCHSET_NUMBER")
    
    if not change_id or not patchset_num:
        info_color('error', "环境变量中缺少 GERRIT_CHANGE_ID 或 GERRIT_PATCHSET_NUMBER")
        sys.exit(1)
        
    # 同步修改内部方法名：gerrit_files_get
    changed_files = ctx.obj.gerrit.gerrit_files_get(change_id, patchset_num)
    if not changed_files:
        info_color('warn', "未检测到变更文件，流程结束。")
        return

    triggered_count = 0
    for p_name, p_config in pipelines.items():
        info_color('info', f"评估流水线: {p_name}")
        should_run, hit_details = should_trigger_pipeline(changed_files, p_config, global_ignore)
        
        if should_run:
            info_color('notes', f"匹配成功，命中文件:\n  " + "\n  ".join(hit_details))
            if dry_run:
                info_color('warn', f"[DRY RUN] 跳过触发，但将会触发: {p_name}")
            else:
                # 同步修改内部方法名：job_trigger
                success = ctx.obj.jenkins.job_trigger(p_name, ENV_VAR_LIST)
                if success:
                    triggered_count += 1
        else:
            info_color('info', f"流水线 {p_name} 未匹配到变更规则")

    info_color('info', f"=== 触发分析结束，共触发 {triggered_count} 个任务 ===")

# ==============================================================================
# 模块 A：Gerrit 打分 (patch_score)
# ==============================================================================

@cli.command()
@click.option('--change-number', '-cn', required=True, help='Gerrit 变更编号')
@click.option('--patch-number', '-pn', required=True, type=int, help='PatchSet 编号')
@click.option('--score', '-s', required=True, type=int, help='打分数值')
@click.option('--label', '-l', default='Verified', help='打分标签 (默认 Verified)')
@click.option('--comment', '-m', default='robot score', help='打分附言')
@click.pass_context
def patch_score_update(ctx, change_number, patch_number, score, label, comment):
    """【打分】给指定 Patch 打分"""
    info_color('info', f"准备给变更 {change_number} 的 Patch {patch_number} 打分...")
    # 同步修改：gerrit_score_post
    success = ctx.obj.gerrit.gerrit_score_post(
        change_number=change_number,
        patch_id=patch_number,
        score=score,
        comment=comment,
        label=label
    )
    if success:
        info_color('notes', "打分操作执行完毕")

@cli.command()
@click.option('--change-number', '-cn', required=True, help='Gerrit 变更编号')
@click.option('--patch-number', '-pn', required=True, type=int, help='PatchSet 编号')
@click.pass_context
def patch_score_get(ctx, change_number, patch_number):
    """【打分】取得 Patch 打分现状"""
    info_color('info', f"查询变更 {change_number} (Patch {patch_number}) 的打分数据...")
    url = f"{ctx.obj.gerrit.base_url}/a/changes/{change_number}?o=LABELS"
    response = ctx.obj.gerrit._send_request('GET', url)
    if response:
        data = ctx.obj.gerrit._handle_response(response)
        labels = data.get('labels', {})
        print(json.dumps(labels, indent=2, ensure_ascii=False))

# ==============================================================================
# 模块 B：Gerrit Checker 插件 (patch_check)
# ==============================================================================

@cli.command()
@click.option('--change-number', '-cn', required=True, help='Gerrit 变更编号')
@click.option('--patch-number', '-pn', required=True, help='PatchSet 编号')
@click.option('--check-uuid', '-uuid', required=True, help='Checker 的 UUID，如果是 "all" 则更新所有')
@click.option('--status', '-st', required=True, type=click.Choice(['SCHEDULING', 'RUNNING', 'SUCCESSFUL', 'FAILED']), help='状态')
@click.option('--is-block', '-b', is_flag=True, help='是否阻塞 (True 代表强制阻断)')
@click.option('--comment', '-m', default='robot score', help='Checker 附言')
@click.pass_context
def patch_check_update(ctx, change_number, patch_number, check_uuid, status, is_block, comment):
    """【检查】给一个 Patch 更新 Checker 状态"""
    info_color('info', f"更新 Checker 状态 [{status}]...")
    
    # 同步修改：gerrit_change_get
    change_data = ctx.obj.gerrit.gerrit_change_get(change_number, int(patch_number))
    if not change_data:
        return
        
    list_url = f"{ctx.obj.gerrit.base_url}/a/changes/{change_number}/revisions/current/checks"
    list_resp = ctx.obj.gerrit._send_request('GET', list_url)
    if not list_resp:
        return
    checks_list = ctx.obj.gerrit._handle_response(list_resp) or []
    
    target_uuids = []
    if check_uuid.lower() == 'all':
        target_uuids = [c.get('checkerUuid') for c in checks_list if c.get('checkerUuid')]
    else:
        target_uuids = [check_uuid]

    for uuid in target_uuids:
        url = f"{ctx.obj.gerrit.base_url}/a/plugins/checks/checks/"
        payload = {
            "checkerUuid": uuid,
            "state": status,
            "message": comment,
            "changeNumber": int(change_number),
            "patchSetNumber": int(patch_number)
        }
        resp = ctx.obj.gerrit._send_request('POST', url, json=payload, headers={"Content-Type": "application/json"})
        if resp:
            info_color('notes', f"成功更新 Checker: {uuid} 为 {status}")

@cli.command()
@click.option('--change-number', '-cn', required=True, help='Gerrit 变更编号')
@click.option('--patch-number', '-pn', required=True, help='PatchSet 编号')
@click.option('--check-uuid', '-uuid', default="", help='指定 Checker UUID，不填则查所有')
@click.pass_context
def patch_check_get(ctx, change_number, patch_number, check_uuid):
    """【检查】查询一个 Patch 所有 Checker 状态"""
    info_color('info', f"查询 Checker 状态 (Change: {change_number}, Patch: {patch_number})...")
    url = f"{ctx.obj.gerrit.base_url}/a/changes/{change_number}/revisions/{patch_number}/checks"
    
    response = ctx.obj.gerrit._send_request('GET', url)
    if response:
        data = ctx.obj.gerrit._handle_response(response)
        if check_uuid:
            filtered_data = [c for c in data if c.get('checkerUuid') == check_uuid]
            print(json.dumps(filtered_data, indent=2))
        else:
            print(json.dumps(data, indent=2))

# ==============================================================================
# 模块 C：Jenkins 流水线控制 (patch_pipeline)
# ==============================================================================

@cli.command()
@click.option('--gerrit-name', '-gn', required=True, help='Gerrit 仓库名')
@click.option('--change-number', '-cn', required=True, help='Gerrit 变更编号')
@click.option('--patch-number', '-pn', required=True, help='PatchSet 编号')
@click.option('--config', '-c', default=DEFAULT_TRIGGER_CONFIG, type=click.Path(exists=True), help='触发规则配置文件')
@click.pass_context
def patch_pipeline_start(ctx, gerrit_name, change_number, patch_number, config):
    """【流水线】根据配置文件规则启动 Pipeline 队列"""
    info_color('info', f"解析配置文件 {config} 尝试触发任务...")
    
    trigger_config = load_json_file(config, "触发规则配置")
    if not trigger_config:
        return
        
    pipelines = trigger_config.get('pipelines', {})
    
    mock_env = {
        "GERRIT_NAME": gerrit_name,
        "GERRIT_CHANGE_NUMBER": change_number,
        "GERRIT_PATCHSET_NUMBER": patch_number
    }
    
    for p_name in pipelines.keys():
        info_color('notes', f"准备触发流水线: {p_name}")
        ctx.obj.jenkins.job_trigger(p_name, mock_env)

@cli.command()
@click.option('--gerrit-name', '-gn', required=True, help='Gerrit 仓库名')
@click.option('--change-number', '-cn', required=True, help='Gerrit 变更编号')
@click.option('--patch-number', '-pn', required=True, help='PatchSet 编号')
@click.pass_context
def patch_pipeline_stop(ctx, gerrit_name, change_number, patch_number):
    """【流水线】停止并取消匹配的所有 Pipeline"""
    ctx.obj.jenkins.pipeline_stop(gerrit_name=gerrit_name, change_number=change_number)

@cli.command()
@click.option('--gerrit-name', '-gn', required=True, help='Gerrit 仓库名')
@click.option('--change-number', '-cn', required=True, help='Gerrit 变更编号')
@click.option('--patch-number', '-pn', required=True, help='PatchSet 编号')
@click.pass_context
def patch_pipeline_get(ctx, gerrit_name, change_number, patch_number):
    """【流水线】获取所有匹配的 Pipeline 执行和队列状态"""
    info_color('info', f"检索 Jenkins 队列和运行中任务 (Gerrit: {gerrit_name}, Change: {change_number})...")
    
    # A. 检索队列
    queue_url = f"{ctx.obj.jenkins.base_url}/queue/api/json?tree=items[id,task[name],actions[parameters[name,value]]]"
    q_resp = ctx.obj.jenkins._send_request('GET', queue_url)
    waiting_jobs = []
    
    if q_resp:
        for item in q_resp.json().get('items', []):
            params = ctx.obj.jenkins._extract_params(item)
            if ctx.obj.jenkins._is_match(params, gerrit_name, change_number):
                waiting_jobs.append({"type": "QUEUE", "id": item.get('id'), "name": item.get('task', {}).get('name')})
                
    # B. 检索运行中
    exec_url = f"{ctx.obj.jenkins.base_url}/computer/api/json?tree=computer[executors[currentExecutable[url,number]]]"
    e_resp = ctx.obj.jenkins._send_request('GET', exec_url)
    running_jobs = []
    
    if e_resp:
        for computer in e_resp.json().get('computer', []):
            for exec_item in computer.get('executors', []):
                executable = exec_item.get('currentExecutable')
                if executable:
                    job_url = executable.get('url')
                    running_jobs.append({"type": "RUNNING", "url": job_url})

    result = {
        "queue_waiting": waiting_jobs,
        "running": running_jobs
    }
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    cli()