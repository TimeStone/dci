import os
import json
import re
from .ci.jenkins import JenkinsClient
from .repo.gerrit import GerritClient
from .common.settings import GlobalSettings
from .common.utils import info_color, matches_pattern

def should_trigger_pipeline(changed_files, pipeline_config, global_ignore_patterns):
    """
    核心逻辑：判断当前流水线是否应该被触发
    返回: (bool: 是否触发, list: 命中的文件列表)
    """
    rules = pipeline_config.get('rules', [])
    if not rules:
        return False, []

    hit_files = []

    for rule in rules:
        rule_id = rule.get('id', 'unknown')
        match_patterns = rule.get('match_paths', [])
        
        # 合并忽略规则：规则级忽略 + 全局忽略
        ignore_patterns = rule.get('ignore_paths', []) + global_ignore_patterns
        
        rule_matched = False
        
        for file in changed_files:
            # 1. 检查是否被忽略
            is_ignored = False
            for pattern in ignore_patterns:
                if matches_pattern(file, pattern):
                    is_ignored = True
                    break
            
            if is_ignored:
                continue
            # 2. 检查是否匹配
            for pattern in match_patterns:
                if matches_pattern(file, pattern):
                    rule_matched = True
                    hit_files.append(f"{file} (Rule: {rule_id})")
                    break # 文件已匹配当前规则，无需检查该文件的其他规则
            
            if rule_matched:
                break # 规则已命中，无需检查该规则下的其他文件
        info_color("debug", f"try check {rule} for {changed_files}: {rule_matched}")
        if rule_matched:
            # 只要有一个规则命中，整个流水线就触发
            return True, hit_files

    return False, []



def trigger_jenkins_job(jenkins_url, job_name, params, auth):
    """执行 Jenkins 远程触发"""
    # 构建 URL: job/{name}/buildWithParameters
    job_url = f"{jenkins_url.rstrip('/')}/job/{job_name}/buildWithParameters"
    
    try:
        # 发送 POST 请求
        # 注意：Jenkins 可能会返回 201 Created 或 200 OK
        response = requests.post(job_url, params=params, auth=auth, timeout=15)
        
        if response.status_code in [200, 201]:
            return True, response.status_code
        else:
            return False, f"{response.status_code}: {response.text}"
            
    except Exception as e:
        return False, str(e)