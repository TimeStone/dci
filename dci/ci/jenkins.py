import requests
from ..common.settings import settings
from ..common.utils import info_color

class JenkinsClient:
    def __init__(self):
        self.base_url = settings.JENKINS_URL.rstrip('/')
        self.user = settings.USER
        self.token = settings.API_TOKEN

    def trigger_job(self, job_name, parameters=None):
        """
        触发 Jenkins 任务
        """
        url = f"{self.base_url}/job/{job_name}/buildWithParameters"
        
        info_color('info', f"正在连接 Jenkins: {self.base_url}")
        info_color('notes', f"触发任务: {job_name}")
        
        # 模拟输出参数
        if parameters:
            for k, v in parameters.items():
                print(f"  - {k}: {v}")

        # 真实环境请取消下面的注释
        # try:
        #     response = requests.post(url, params=parameters, auth=(self.user, self.token))
        #     if response.status_code in [200, 201]:
        #         info_color('notes', "触发成功")
        #     else:
        #         info_color('error', f"触发失败: {response.status_code} - {response.text}")
        # except Exception as e:
        #     info_color('error', str(e))
        
        print(f"  -> [Mock] HTTP POST {url}")