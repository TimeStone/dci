import json
import requests
from requests.auth import HTTPBasicAuth
from ..common.settings import settings, IS_DRY_RUN
from ..common.utils import info_color


class GerritClient:
    def __init__(self, base_url=None, username=None, token=None):
        # 优先使用传入的参数，若无则读取 settings 中的配置
        self.base_url = (base_url or settings.GERRIT_URL).rstrip('/')
        self.user = username or settings.GERRIT_USER
        self.token = token or settings.GERRIT_PASSWORD
        self.auth = (self.user, self.token)

    def _handle_response(self, response):
        """
        公共函数：处理 Gerrit 特有的 XSSI 保护前缀并解析 JSON
        """
        text_content = response.text
        if text_content.startswith(")]}'"):
            text_content = text_content[4:]
        try:
            return json.loads(text_content)
        except json.JSONDecodeError:
            info_color('error', "JSON 解析失败")
            return None

    def _send_request(self, method, url, **kwargs):
        """
        公共函数：统一发送 HTTP 请求，处理异常
        """
        kwargs.setdefault('auth', self.auth)
        kwargs.setdefault('timeout', 10)
        
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            error_text = e.response.text
            if error_text.startswith(")]}'"):
                error_text = error_text[4:]
            info_color('error', f"HTTP 错误 ({e.response.status_code}): {error_text.strip()}")
            return None
        except requests.exceptions.RequestException as e:
            info_color('error', f"请求异常: {e}")
            return None

    def score_change(self, change_id, score, label="Verified"):
        """
        给 Gerrit 变更打分
        """
        url = f"{self.base_url}/a/changes/{change_id}/revisions/current/review"
        
        info_color('info', f"正在连接 Gerrit: {self.base_url}")
        info_color('notes', f"准备给变更 {change_id} 打分: {label}={score}")
        
        payload = {
            "labels": {
                label: score
            }
        }

        print(f"  -> [Mock] HTTP POST {url}")
        print(f"  -> [Mock] Payload: {payload}")
        return True

    def get_gerrit_files(self, change_id, patchset_number=0):
        """
        调用 Gerrit API 获取指定 Patchset 的文件列表
        """
        if patchset_number == 0:
            patchset_number = 'current'
            
        api_url = f"{self.base_url}/a/changes/{change_id}/revisions/{patchset_number}/files"

        if IS_DRY_RUN:
            info_color('debug', f"正在获取 Patchset {patchset_number} 的文件列表 {api_url}")
            return ["gerrit_repo1:aa/path1.xml", "gerrit_repo1:bb/path2.xml", "gerrit_repo1:cc/path1.c"]

        info_color('info', f"正在获取 Patchset {patchset_number} 的文件列表...")
        response = self._send_request('GET', api_url)
        if not response:
            return []

        data = self._handle_response(response)
        if not data:
            return []
            
        files = list(data.keys())
        info_color('notes', f"成功获取 {len(files)} 个变更文件")
        return files

    def get_gerrit_change(self, change_number, patch_id=None):
        """
        获取 Gerrit Change 的详细信息，包括项目、分支、所有者和文件列表
        """
        # 1. 获取 Change 的元数据
        option = "ALL_REVISIONS" if patch_id is not None else "CURRENT_REVISION"
        change_info_url = f"{self.base_url}/a/changes/{change_number}?o={option}"
        
        response = self._send_request('GET', change_info_url)
        if not response:
            return None
            
        change_data = self._handle_response(response)
        if not change_data:
            return None

        project_name = change_data.get('project')
        branch_name = change_data.get('branch')
        owner_name = change_data.get('owner', {}).get('name', 'Unknown')
        
        # 2. 确定目标 Revision ID (Commit Hash)
        target_revision_id = None
        if patch_id is None:
            target_revision_id = change_data.get('currentRevision')
        else:
            revisions = change_data.get('revisions', {})
            for rev_hash, rev_info in revisions.items():
                if rev_info.get('number') == patch_id:
                    target_revision_id = rev_hash
                    break
            
            if not target_revision_id:
                info_color('error', f"未找到 Patch Set 编号: {patch_id}")
                return None

        if not target_revision_id:
            info_color('error', "无法确定 Revision ID")
            return None

        # 3. 获取文件列表
        files_url = f"{self.base_url}/a/changes/{change_number}/revisions/{target_revision_id}/files"
        files_response = self._send_request('GET', files_url)
        if not files_response:
            return None

        files_data = self._handle_response(files_response)
        if not files_data:
            return None

        formatted_files = [f"{project_name}:{file_path}" for file_path in files_data.keys()]

        return {
            "projects": [project_name],
            "branch": branch_name,
            "owners": [owner_name],
            "files": formatted_files
        }

    def post_gerrit_score(self, change_number, patch_id=0, score=0, comment="default comment", label="Code-Review"):
        """
        给 Gerrit Change 打分 (Review)
        """
        # 1. 确定 Revision ID
        option = "CURRENT_REVISION" if patch_id == 0 else "ALL_REVISIONS"
        change_info_url = f"{self.base_url}/a/changes/{change_number}?o={option}"
        
        response = self._send_request('GET', change_info_url)
        if not response:
            return False

        change_data = self._handle_response(response)
        if not change_data:
            return False

        revision_id = None
        if patch_id == 0:
            revision_id = change_data.get('currentRevision')
        else:
            revisions = change_data.get('revisions', {})
            for rev_hash, rev_info in revisions.items():
                if rev_info.get('number') == patch_id:
                    revision_id = rev_hash
                    break
        
        if not revision_id:
            info_color('error', f"无法找到对应 Patch 的 Revision ID")
            return False

        # 2. 构造 Review 请求
        review_url = f"{self.base_url}/a/changes/{change_number}/revisions/{revision_id}/review"
        review_payload = {
            "labels": {
                label: score
            },
            "message": comment
        }
        
        headers = {"Content-Type": "application/json"}
        put_response = self._send_request('PUT', review_url, json=review_payload, headers=headers)
        
        if put_response:
            info_color('notes', f"打分成功！Change: {change_number}, Score: {score}")
            return True
        return False

    def post_gerrit_score_by_topic(self, topic_name, score=1, comment="Auto-score via script", label="Code-Review"):
        """
        根据 Topic 字符串，给该 Topic 下所有 OPEN 状态的 Change 打分
        """
        search_query = f"topic:{topic_name}+status:open"
        search_url = f"{self.base_url}/a/changes/?q={search_query}"
        
        info_color('info', f"正在搜索 Topic {topic_name} 下的 Open Changes...")
        
        search_response = self._send_request('GET', search_url)
        if not search_response:
            return {"success": 0, "failed": 0}

        search_results = self._handle_response(search_response)
        if not search_results:
            info_color('info', f"Topic {topic_name} 下没有发现 Open 状态的 Change")
            return {"success": 0, "failed": 0}

        info_color('notes', f"找到 {len(search_results)} 个 Open Change，准备开始打分...")
        
        success_count = 0
        failed_count = 0
        
        for change_summary in search_results:
            change_id = change_summary.get('id')
            change_num = change_summary.get('_number')
            current_revision = change_summary.get('current_revision')
            
            if not current_revision:
                info_color('error', f"Change {change_num} 缺少 revision 信息，跳过")
                failed_count += 1
                continue

            review_url = f"{self.base_url}/a/changes/{change_id}/revisions/{current_revision}/review"
            review_payload = {
                "labels": {
                    label: score
                },
                "message": comment
            }
            
            headers = {"Content-Type": "application/json"}
            put_response = self._send_request('PUT', review_url, json=review_payload, headers=headers)
            
            if put_response:
                info_color('notes', f"Change {change_num}: 打分 {score} 成功")
                success_count += 1
            else:
                info_color('error', f"Change {change_num}: 打分失败")
                failed_count += 1

        return {"success": success_count, "failed": failed_count}