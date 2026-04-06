import sys
import os
import json
import responses

# --- 智能路径注入 ---
# 获取当前脚本 (mock_runner.py) 所在的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
# 它的上一级目录，即包含 'dci' 文件夹的那个目录 (例如 /mnt/d/work/dci)
project_root = os.path.dirname(current_dir)

# 如果 project_root 不在 sys.path 中，就把它加进去。
# 这样无论在哪个目录下执行此脚本，Python 都能正确识别 'from dci.xxx import xxx'
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 此时再安全的导入 dci 包
from dci.cli import cli


GERRIT_BASE = "http://gerrit.example.com"
JENKINS_BASE = "http://jenkins.example.com"

def load_mock_data():
    """从指定的 resource 目录中载入 mock 数据"""
    # 拼接出 resource/test/data/cli_test.json 的绝对路径
    json_path = os.path.join(current_dir, "resource", "test", "data", "cli_test.json")
    
    if not os.path.exists(json_path):
        print(f"❌ 找不到 Mock 配置文件: {json_path}")
        print(f"💡 请确保该文件存在于您的 dci 目录树中。")
        sys.exit(1)
        
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def init_mocks(data):
    """初始化所有的 Mock 路由与数据"""
    
    # Gerrit 专用的拼接辅助函数：加上防 XSSI 攻击的前缀
    def gerrit_body(sub_data_key):
        content = data['gerrit'][sub_data_key]
        return b")]}'\n" + json.dumps(content).encode('utf-8')

    # ---------------------------------------------------------
    # 1. Gerrit Mock 路由
    # ---------------------------------------------------------
    
    # 取得打分现状 (patch_score_get)
    responses.add(
        responses.GET,
        f"{GERRIT_BASE}/a/changes/12345?o=LABELS",
        body=gerrit_body("labels_get"),
        status=200,
        content_type="application/json"
    )

    # 提交打分 (patch_score_update)
    responses.add(
        responses.PUT,
        # 匹配任意 PatchSet 结尾的 review 路径
        re=f"{GERRIT_BASE}/a/changes/12345/revisions/.*/review",
        body=gerrit_body("score_update_success"),
        status=200,
        content_type="application/json"
    )

    # 获取 Checker 状态列表 (patch_check_get)
    responses.add(
        responses.GET,
        f"{GERRIT_BASE}/a/changes/12345/revisions/1/checks",
        body=gerrit_body("checks_get_list"),
        status=200,
        content_type="application/json"
    )

    # 提交/修改 Checker (patch_check_update)
    responses.add(
        responses.POST,
        f"{GERRIT_BASE}/a/plugins/checks/checks/",
        body=gerrit_body("check_update_success"),
        status=200,
        content_type="application/json"
    )

    # ---------------------------------------------------------
    # 2. Jenkins Mock 路由
    # ---------------------------------------------------------

    # 获取队列状态 (patch_pipeline_get)
    responses.add(
        responses.GET,
        f"{JENKINS_BASE}/queue/api/json?tree=items[id,task[name],actions[parameters[name,value]]]",
        json=data['jenkins']['queue_get'],
        status=200
    )

    # 获取运行中任务 (patch_pipeline_get)
    responses.add(
        responses.GET,
        f"{JENKINS_BASE}/computer/api/json?tree=computer[executors[currentExecutable[url,number]]]",
        json=data['jenkins']['computer_get'],
        status=200
    )

    # 触发与取消 (patch_pipeline_start / patch_pipeline_stop)
    responses.add(responses.POST, f"{JENKINS_BASE}/job/my-build-job/buildWithParameters", status=201)
    responses.add(responses.POST, f"{JENKINS_BASE}/job/my-build-job/42/stop", status=200)


if __name__ == '__main__':
    # 载入纯数据
    mock_data = load_mock_data()
    
    # 开启拦截并装载
    responses.start()
    init_mocks(mock_data)
    
    print("🤖 [Mock Mode] 数据隔离拦截已开启，正在执行 DCI 主程序...")
    
    try:
        # 透传命令行参数执行
        cli(sys.argv[1:])
    finally:
        responses.stop()