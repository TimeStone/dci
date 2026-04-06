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
GLOBAL_CONFIG_PATH = "dci/conf/conf_global.json"


# 上下文对象
class Context:
    def __init__(self):
        self.jenkins = JenkinsClient()
        self.gerrit = GerritClient()

# ... 上面的 import 和 cli 定义保持不变 ...


# ... 下面的 trigger 和 score 命令保持不变 ...
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
    # 直接调用打印函数，享受你的随机颜色
    print_banner()
    # 这里不需要写 return，Click 会自动处理

@cli.command()
@click.option('--config', '-c', required=True, type=click.Path(exists=True), help='触发规则配置文件路径 (JSON)')
@click.option('--dry-run', is_flag=True, help='仅打印执行计划，不实际触发')
@click.pass_context
def trigger(ctx, config, dry_run):
    """
    主函数：解析配置，获取变更，匹配规则，触发下游任务
    """
    dry_run =  dry_run or IS_DRY_RUN
    info_color('info', "=== 开始 Gerrit CI 触发分析 ===")
    info_color('info', f"config: {config}") 
    info_color('info', f"dry_run: {dry_run}") 
    # 1. 加载全局配置 (认证信息)
    global_conf = load_json_file(GLOBAL_CONFIG_PATH, "全局配置")
    if not global_conf:
        sys.exit(1)
        
    # 提取认证信息
    jenkins_url = settings.JENKINS_URL
    jenkins_user = settings.JENKINS_USER
    jenkins_token = settings.JENKINS_PASSWORD
    gerrit_url = settings.GERRIT_URL
    gerrit_user = settings.GERRIT_USER
    gerrit_token = settings.GERRIT_PASSWORD
    
    # 校验必要配置
    if not all([jenkins_url, jenkins_user, jenkins_token, gerrit_url]):
        info_color('error', "全局配置中缺少必要的 URL 或认证信息")
        sys.exit(1)
        
    gerrit_auth = HTTPBasicAuth(gerrit_user, gerrit_token)
    jenkins_auth = (jenkins_user, jenkins_token)

    # 2. 加载业务触发配置
    trigger_config = load_json_file(config, "触发规则配置")
    info_color("debug", f"trigger_config: {trigger_config}")
    if not trigger_config:
        sys.exit(1)
        
    pipelines = trigger_config.get('pipelines', {})
    global_ignore = trigger_config.get('global_ignore', {}).get('paths', [])
    info_color("debug", f"pipelines: {pipelines}")
    # 3. 获取环境变量与 Gerrit 信息
    change_id = os.getenv("GERRIT_CHANGE_ID")
    patchset_num = os.getenv("GERRIT_PATCHSET_NUMBER")
    
    if not change_id or not patchset_num:
        info_color('error', "环境变量中缺少 GERRIT_CHANGE_ID 或 GERRIT_PATCHSET_NUMBER")
        sys.exit(1)
        
    # 4. 获取变更文件列表
    client = GerritClient()  # 会自动读取 settings 里的配置
    changed_files = client.get_gerrit_files(change_id, patchset_num)
    #changed_files = get_gerrit_files(gerrit_url, gerrit_auth, change_id, patchset_num)
    if not changed_files:
        info_color('warn', "未检测到变更文件，流程结束。")
        return
    info_color("debug", changed_files)
    # 5. 准备下游触发参数
    trigger_params = ENV_VAR_LIST
    info_color('info', f"已收集 {len(trigger_params)} 个环境变量参数。")

    # 6. 遍历流水线进行匹配
    triggered_count = 0
    
    for p_name, p_config in pipelines.items():
        info_color('info', f"评估流水线: {p_name}")
        
        should_run, hit_details = should_trigger_pipeline(changed_files, p_config, global_ignore)
        
        if should_run:
            info_color('notes', f"匹配成功，命中文件:\n  " + "\n  ".join(hit_details))
            
            if dry_run:
                info_color('warn', f"[DRY RUN] 跳过触发，但将会触发: {p_name}")
            else:
                info_color('notes', f"正在触发流水线: {p_name} ...")
                success, result = trigger_jenkins_job(jenkins_url, p_name, trigger_params, jenkins_auth)
                
                if success:
                    info_color('notes', f"成功触发 Job '{p_name}' (HTTP {result})")
                    triggered_count += 1
                else:
                    info_color('error', f"触发 Job '{p_name}' 失败: {result}")
        else:
            info_color('info', f"流水线 {p_name} 未匹配到变更规则")

    info_color('info', f"=== 触发分析结束，共触发 {triggered_count} 个任务 ===")


@cli.command()
@click.option('--change-id', '-cid', required=True, help='Gerrit 变更ID')
@click.option('--score', '-s', type=int, default=1, help='打分数值 (+1, -1, etc)')
@click.option('--label', '-l', default='Verified', help='打分标签')
@click.pass_context
def score(ctx, change_id, score, label):
    """给 Gerrit 变更打分"""
    info_color('info', "开始执行打分操作...")
    ctx.obj.gerrit.score_change(change_id, score, label)