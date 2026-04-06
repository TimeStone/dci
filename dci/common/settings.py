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
        if not config_path:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'conf', 'conf_global.json')
        
        self.config_path = os.path.abspath(config_path)
        self.user_config_path = os.path.join(os.path.expanduser("~"), ".dci.json")
        
        # 1. 字典定义
        self.CONFIG_DICT = {}
        self.USER_CONFIG_DICT = {}
        
        # 保留原有硬编码成员变量
        self.GERRIT_URL = ""
        self.GERRIT_USER = ""
        self.GERRIT_PASSWORD = ""
        self.JENKINS_URL = ""
        self.JENKINS_USER = ""
        self.JENKINS_PASSWORD = ""        
        
        self._load_config()
        self._load_user_config()

    def _load_config(self):
        if not os.path.exists(self.config_path):
            info_color('warn', f"全局配置文件未找到: {self.config_path}，使用默认空配置")
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.CONFIG_DICT.update(config)
            
            # 保留原有的硬编码成员赋值
            self.GERRIT_URL = config.get('gerrit_url', '')
            self.GERRIT_USER = config.get('gerrit_user', '')
            self.GERRIT_PASSWORD = config.get('gerrit_password', '')
            self.JENKINS_URL = config.get('jenkins_url', '')
            self.JENKINS_USER = config.get('jenkins_user', '')
            self.JENKINS_PASSWORD = config.get('jenkins_password', '')
            info_color('notes', f"已加载全局配置: {self.config_path}")
            
        except Exception as e:
            info_color('error', f"加载全局配置失败: {e}")

    def _load_user_config(self):
        if not os.path.exists(self.user_config_path):
            return
        try:
            with open(self.user_config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                
            self.USER_CONFIG_DICT.update(user_config)
            info_color('notes', f"已加载用户配置: {self.user_config_path}")
            
        except Exception as e:
            info_color('error', f"加载用户配置失败: {e}")

    def get_config(self, key, defaultValue=None):
        """
        获取配置项
        优先级：1. 环境变量 -> 2. 用户配置 -> 3. 全局配置 -> 4. 默认值
        """
        # 1. 优先查环境变量 (将 key 转为全大写，符合环境变量常识，如 gerrit_url -> GERRIT_URL)
        env_key = key.upper()
        env_val = os.getenv(env_key)
        if env_val is not None:
            return env_val

        # 2. 其次查用户配置 ~/.dci.json
        if key in self.USER_CONFIG_DICT:
            return self.USER_CONFIG_DICT[key]
        
        # 3. 再者查全局配置
        if key in self.CONFIG_DICT:
            return self.CONFIG_DICT[key]
        
        # 4. 都找不到，返回默认值
        return defaultValue


# 单例模式
settings = GlobalSettings()