增强下面这个trigger函数
1： 从config文件内容如下：
{
  "meta": {
    "version": "1.0",
    "desc": "Gerrit 触发配置主文件，定义流水线与文件路径的映射关系"
  },
  "global_ignore": {
    "desc": "全局忽略规则，所有流水线默认继承这些忽略项",
    "paths": [
      ".*\\.md$",
      "docs/.*",
      "LICENSE",
      "\\.gitignore"
    ]
  },
  "pipelines": {
    "p1_pipeline": {
      "desc": "核心业务模块流水线，负责后端服务的构建与测试",
      "mandatory_default": true,
      "rules": [
        {
          "id": "rule_core",
          "desc": "匹配核心代码库的变更，必须通过",
          "match_paths": [
            "gerrit_repo1:src/main/.*",
            "gerrit_repo1:src/test/.*"
          ],
          "ignore_paths": [
            "src/test/resources/.*"
          ],
          "mandatory": true
        },
        {
          "id": "rule_common",
          "desc": "匹配公共库变更，作为可选检查",
          "match_paths": [
            "gerrit_repo2:.*"
          ],
          "mandatory": false
        }
      ]
    },
    "p2_pipeline": {
      "desc": "前端构建流水线，仅关注前端仓库",
      "mandatory_default": false,
      "rules": [
        {
          "id": "rule_fe",
          "desc": "前端核心目录变更",
          "match_paths": [
            "gerrit_repo2:frontend/.*"
          ],
          "mandatory": true
        }
      ]
    }
  }
}


2： 从环境变量中取得gerrit trigger的全部信息，如：
        string(name: "BRANCH_NAME", defaultValue: DEFAULT_BRANCH_NAME, description: "the BRANCH_NAME to build")
        string(name: "GERRIT_BRANCH", defaultValue: DEFAULT_BRANCH_NAME, description: "the GERRIT_BRANCH to build")
        string(name: "NODE_LABEL", defaultValue: DEFAULT_NODE_LABEL, description: "the label of node to build")
        string(name: "JENKINS_BUILD_TYPE", defaultValue: 'ci', description: "JENKINS_BUILD_TYPE to build")
        string(name: "GERRIT_PROJECT", defaultValue: '', description: "GERRIT_PROJECT to build")
        string(name: "GERRIT_REFSPEC", defaultValue: '', description: "GERRIT_REFSPEC to build")
        string(name: "GERRIT_EVENT_TYPE", defaultValue: '', description: "the GERRIT_EVENT_TYPE to build")
        string(name: "GERRIT_EVENT_HASH", defaultValue: '', description: "the GERRIT_EVENT_HASH to build")
        string(name: "GERRIT_CHANGE_WIP_STATE", defaultValue: '', description: "GERRIT_CHANGE_WIP_STATE to build")
        string(name: "GERRIT_CHANGE_PRIVATE_STATE", defaultValue: '', description: "GERRIT_CHANGE_PRIVATE_STATE to build")
        string(name: "GERRIT_TOPIC", defaultValue: '', description: "the GERRIT_TOPIC to build")
        string(name: "GERRIT_CHANGE_NUMBER", defaultValue: '', description: "GERRIT_CHANGE_NUMBER to build")
        string(name: "GERRIT_CHANGE_ID", defaultValue: '', description: "GERRIT_CHANGE_ID to build")
        string(name: "GERRIT_PATCHSET_NUMBER", defaultValue: '', description: "GERRIT_PATCHSET_NUMBER to build")
        string(name: "GERRIT_PATCHSET_REVISION", defaultValue: '', description: "GERRIT_PATCHSET_REVISION to build")
        string(name: "GERRIT_CHANGE_SUBJECT", defaultValue: '', description: "GERRIT_CHANGE_SUBJECT to build")
        string(name: "GERRIT_CHANGE_COMMIT_MESSAGE", defaultValue: '', description: "GERRIT_CHANGE_COMMIT_MESSAGE to build")
        string(name: "GERRIT_CHANGE_URL", defaultValue: '', description: "GERRIT_CHANGE_URL to build")
        string(name: "GERRIT_CHANGE_OWNER", defaultValue: '', description: "GERRIT_CHANGE_OWNER to build")
        string(name: "GERRIT_CHANGE_OWNER_NAME", defaultValue: '', description: "GERRIT_CHANGE_OWNER_NAME to build")
        string(name: "GERRIT_CHANGE_OWNER_EMAIL", defaultValue: '', description: "GERRIT_CHANGE_OWNER_EMAIL to build")
        string(name: "GERRIT_PATCHSET_UPLOADER", defaultValue: '', description: "GERRIT_PATCHSET_UPLOADER to build")
        string(name: "GERRIT_PATCHSET_UPLOADER_NAME", defaultValue: '', description: "GERRIT_PATCHSET_UPLOADER_NAME to build")
        string(name: "GERRIT_PATCHSET_UPLOADER_EMAIL", defaultValue: '', description: "GERRIT_PATCHSET_UPLOADER_EMAIL to build")
  3:  根据环境变量中的


def trigger(ctx, config, change_id, dry_run):
    """解析配置文件并触发 Hub CI 任务"""
    info_color('info', "开始分析触发规则...")
    
    # 1. 加载配置
    try:
        with open(config, 'r', encoding='utf-8') as f:
            data = json.load(f)
        info_color('notes', f"成功加载配置: {os.path.basename(config)}")
    except Exception as e:
        info_color('error', f"读取配置文件失败: {e}")
        return

    # 2. 模拟获取变更文件列表
    # 在实际场景中，这里应该调用 ctx.obj.gerrit.get_files(change_id)
    mock_changed_files = [
        "gerrit_repo1:src/main/java/App.java", 
        "docs/readme.md",
        "gerrit_repo2:frontend/main.js"
    ]
    info_color('info', f"检测到变更文件: {mock_changed_files}")

    # 3. 匹配流水线
    pipelines = data.get('pipelines', {})
    global_ignore = data.get('global_ignore', {}).get('paths', [])
    
    triggered_count = 0

    for p_name, p_config in pipelines.items():
        should_run = False
        
        # 简单的匹配逻辑演示
        for rule in p_config.get('rules', []):
            match_paths = rule.get('match_paths', [])
            ignore_paths = rule.get('ignore_paths', []) + global_ignore
            
            # 检查是否有文件匹配
            for file in mock_changed_files:
                # 检查忽略
                if any(re.match(pat, file) for pat in ignore_paths):
                    continue
                
                # 检查匹配
                if any(re.match(pat, file) for pat in match_paths):
                    should_run = True
                    info_color('notes', f"规则 '{rule.get('id')}' 命中文件: {file}")
                    break
            if should_run: break

        if should_run:
            if dry_run:
                info_color('warn', f"[DRY RUN] 将会触发流水线: {p_name}")
            else:
                info_color('notes', f"触发流水线: {p_name}")
                params = {
                    "GERRIT_CHANGE_ID": change_id,
                    "GERRIT_EVENT_TYPE": "patchset-created"
                }
                ctx.obj.jenkins.trigger_job(p_name, params)
            triggered_count += 1

    if triggered_count == 0:
        info_color('warn', "没有匹配的流水线被触发")


