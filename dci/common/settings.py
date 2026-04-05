import json
import os
from .utils import info_color

IS_DRY_RUN = True

ENV_VAR_LIST = [
    "BRANCH_NAME", "GERRIT_BRANCH", "NODE_LABEL", "JENKINS_BUILD_TYPE",
    "GERRIT_PROJECT", "GERRIT_REFSPEC", "GERRIT_EVENT_TYPE", "GERRIT_EVENT_HASH",
    "GERRIT_CHANGE_WIP_STATE", "GERRIT_CHANGE_PRIVATE_STATE", "GERRIT_TOPIC",
    "GERRIT_CHANGE_NUMBER", "GERRIT_CHANGE_ID", "GERRIT_PATCHSET_NUMBER",
    "GERRIT_PATCHSET_REVISION", "GERRIT_CHANGE_SUBJECT", "GERRIT_CHANGE_COMMIT_MESSAGE",
    "GERRIT_CHANGE_URL", "GERRIT_CHANGE_OWNER", "GERRIT_CHANGE_OWNER_NAME",
    "GERRIT_CHANGE_OWNER_EMAIL", "GERRIT_PATCHSET_UPLOADER", "GERRIT_PATCHSET_UPLOADER_NAME",
    "GERRIT_PATCHSET_UPLOADER_EMAIL"
]


class GlobalSettings:
    def __init__(self, config_path=None):
        # 默认路径
        if not config_path:
            # 假设 conf 文件夹与 common 同级或在上一级
            config_path = os.path.join(os.path.dirname(__file__), '..', 'conf', 'conf_global.json')
        
        self.config_path = os.path.abspath(config_path)
        self.GERRIT_URL = ""
        self.JENKINS_URL = ""
        self.USER = ""
        self.API_TOKEN = ""
        
        self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_path):
            info_color('warn', f"全局配置文件未找到: {self.config_path}，使用默认空配置")
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.GERRIT_URL = config.get('gerrit_url', '')
            self.JENKINS_URL = config.get('jenkins_url', '')
            self.USER = config.get('user', '')
            self.API_TOKEN = config.get('api_token', '')
            
            info_color('notes', f"已加载全局配置: {self.config_path}")
            
        except Exception as e:
            info_color('error', f"加载全局配置失败: {e}")



def get_job_params(env_list=ENV_VAR_LIST):
    """从系统环境变量中提取 Gerrit 相关参数"""
    params = {}
    missing_vars = []
    
    for key in env_list:
        val = os.getenv(key)
        if val:
            params[key] = val
        else:
            # 仅记录关键变量缺失，非关键变量可选
            if key in ["GERRIT_CHANGE_ID", "GERRIT_PATCHSET_NUMBER"]:
                missing_vars.append(key)
    
    if missing_vars:
        info_color('warn', f"缺少关键环境变量: {', '.join(missing_vars)}")
        
    return params


# 单例模式，供其他模块导入使用
settings = GlobalSettings()

