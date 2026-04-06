import pytest
from click.testing import CliRunner
from dci.cli import cli, DEFAULT_TRIGGER_CONFIG

@pytest.fixture
def runner():
    return CliRunner()

# ==============================================================================
# 模块 A：Gerrit 打分 (patch_score) 测试
# ==============================================================================

def test_patch_score_update_success(runner, mocker):
    """测试 patch_score_update 命令在正常流转下调用 gerrit_score_post"""
    # 模拟底层的 GerritClient.gerrit_score_post 方法
    mock_post = mocker.patch('dci.repo.gerrit.GerritClient.gerrit_score_post', return_value=True)
    
    result = runner.invoke(cli, [
        'patch_score_update', 
        '-cn', '12345', 
        '-pn', '1', 
        '-s', '2', 
        '-l', 'Verified', 
        '-m', 'LGTM'
    ])
    
    assert result.exit_code == 0
    # 验证底层的重命名函数是否以正确的参数被调用
    mock_post.assert_called_once_with(
        change_number='12345',
        patch_id=1,
        score=2,
        comment='LGTM',
        label='Verified'
    )
    assert "打分操作执行完毕" in result.output

# ==============================================================================
# 模块 B：Gerrit Checker 插件 (patch_check) 测试
# ==============================================================================

def test_patch_check_update_specific_uuid(runner, mocker):
    """测试 patch_check_update 更新指定 uuid 的 Checker 状态"""
    # 模拟获取变更
    mocker.patch('dci.repo.gerrit.GerritClient.gerrit_change_get', return_value={"id": "some_id"})
    # 模拟获取当前 checks 列表
    mocker.patch('dci.repo.gerrit.GerritClient._send_request', return_value=mocker.Mock(status_code=200))
    mocker.patch('dci.repo.gerrit.GerritClient._handle_response', return_value=[{"checkerUuid": "my-checker"}])
    
    result = runner.invoke(cli, [
        'patch_check_update', 
        '-cn', '12345', 
        '-pn', '1', 
        '-uuid', 'my-checker', 
        '-st', 'SUCCESSFUL'
    ])
    
    assert result.exit_code == 0
    assert "成功更新 Checker: my-checker 为 SUCCESSFUL" in result.output

# ==============================================================================
# 模块 C：Jenkins 流水线控制 (patch_pipeline) 测试
# ==============================================================================

def test_patch_pipeline_start_with_default_config(runner, mocker):
    """测试 patch_pipeline_start 命令在不传 -c 时的默认路径机制"""
    # 模拟加载全局配置，返回一条流水线
    mocker.patch('dci.cli.load_json_file', return_value={
        "pipelines": {"test-pipeline": {}}
    })
    # 模拟 Jenkins 触发
    mock_trigger = mocker.patch('dci.ci.jenkins.JenkinsClient.job_trigger', return_value=True)
    
    # 假设默认配置文件存在，不让 click.Path(exists=True) 报错
    mocker.patch('os.path.exists', return_value=True)
    
    result = runner.invoke(cli, [
        'patch_pipeline_start', 
        '-gn', 'my-repo', 
        '-cn', '12345', 
        '-pn', '1'
    ])
    
    assert result.exit_code == 0
    # 验证是否默认去主程序目录寻找 trigger_config.json
    assert DEFAULT_TRIGGER_CONFIG in result.output
    # 验证是否成功调用 job_trigger
    mock_trigger.assert_called_once()