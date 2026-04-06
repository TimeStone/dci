import requests
from ..common.settings import settings
from ..common.utils import info_color


class JenkinsClient:
    def __init__(self, base_url=None, username=None, token=None):
        self.base_url = (base_url or settings.JENKINS_URL).rstrip('/')
        self.user = username or settings.JENKINS_USER
        self.token = settings.JENKINS_PASSWORD
        self.auth = (self.user, self.token)

    def _get_crumb(self):
        """获取 CSRF Crumb"""
        crumb_url = f"{self.base_url}/crumbIssuer/api/json"
        try:
            response = requests.get(crumb_url, auth=self.auth, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {data.get('crumbRequestField'): data.get('crumb')}
            return {}
        except Exception:
            return {}

    def _send_request(self, method, url, **kwargs):
        """统一发送 HTTP 请求"""
        kwargs.setdefault('auth', self.auth)
        kwargs.setdefault('timeout', 15)
        
        headers = kwargs.get('headers', {})
        if method.upper() in ['POST', 'PUT', 'DELETE']:
            headers.update(self._get_crumb())
        kwargs['headers'] = headers

        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            info_color('error', f"Jenkins 请求失败: {e}")
            return None

    def trigger_job(self, job_name, parameters=None):
        """触发 Jenkins 任务"""
        path = "buildWithParameters" if parameters else "build"
        url = f"{self.base_url}/job/{job_name}/{path}"
        response = self._send_request('POST', url, params=parameters)
        if response:
            info_color('notes', f"成功触发任务: {job_name}")
            return True
        return False

    def pipeline_stop(self, gerrit_name, change_number, pipelineName=""):
        """
        查找并停止/取消与指定 Gerrit 信息匹配的任务。
        可以指定 pipelineName，否则搜索所有 pipeline。
        """
        target_info = f"GERRIT_NAME={gerrit_name}, GERRIT_CHANGE_NUMBER={change_number}"
        if pipelineName:
            info_color('info', f"正在查找并清理流水线 {pipelineName} 中匹配 {target_info} 的任务...")
        else:
            info_color('info', f"正在全局查找并清理匹配 {target_info} 的所有任务...")
        
        # 1. 清理队列中等待的任务
        self._cancel_queue_items(gerrit_name, change_number, pipelineName)
        
        # 2. 终止正在运行的任务
        self._abort_running_jobs(gerrit_name, change_number, pipelineName)

    def _cancel_queue_items(self, gerrit_name, change_number, pipelineName):
        """取消队列中匹配的任务"""
        # 接口拉取队列中任务的 ID、任务名以及参数
        queue_url = f"{self.base_url}/queue/api/json?tree=items[id,task[name],actions[parameters[name,value]]]"
        response = self._send_request('GET', queue_url)
        if not response:
            return

        items = response.json().get('items', [])
        for item in items:
            task_name = item.get('task', {}).get('name')
            
            # 如果指定了名字，但不匹配，则跳过
            if pipelineName and task_name != pipelineName:
                continue
                
            params = self._extract_params(item)
            if self._is_match(params, gerrit_name, change_number):
                item_id = item.get('id')
                info_color('notes', f"正在从队列中取消任务: {task_name} (ID: {item_id})")
                self._send_request('POST', f"{self.base_url}/queue/cancelItem?id={item_id}")

    def _abort_running_jobs(self, gerrit_name, change_number, pipelineName):
        """终止正在运行的匹配任务"""
        # 通过 computer 接口获取所有执行器上正在执行的任务实例 URL
        executors_url = f"{self.base_url}/computer/api/json?tree=computer[executors[currentExecutable[url,number]]]"
        response = self._send_request('GET', executors_url)
        if not response:
            return

        computers = response.json().get('computer', [])
        for computer in computers:
            for executor in computer.get('executors', []):
                executable = executor.get('currentExecutable')
                if not executable:
                    continue
                
                job_url = executable.get('url').rstrip('/')
                
                # 如果指定了 pipelineName，通过 URL 路径快速过滤（Jenkins job URL 包含 /job/job_name/）
                if pipelineName and f"/job/{pipelineName}/" not in job_url:
                    continue
                
                # 获取该特定运行实例的参数
                detail_url = f"{job_url}/api/json?tree=actions[parameters[name,value]]"
                detail_resp = self._send_request('GET', detail_url)
                if not detail_resp:
                    continue

                params = self._extract_params(detail_resp.json())
                if self._is_match(params, gerrit_name, change_number):
                    info_color('notes', f"正在停止运行中的任务: {job_url}")
                    self._send_request('POST', f"{job_url}/stop")

    def _extract_params(self, data):
        """从 Jenkins API 结构中提取参数字典"""
        params = {}
        actions = data.get('actions', [])
        for action in actions:
            parameters = action.get('parameters', [])
            if parameters:
                for p in parameters:
                    params[p.get('name')] = p.get('value')
        return params

    def _is_match(self, params, gerrit_name, change_number):
        """逻辑判断参数是否匹配"""
        return (str(params.get('GERRIT_NAME')) == str(gerrit_name) and 
                str(params.get('GERRIT_CHANGE_NUMBER')) == str(change_number))