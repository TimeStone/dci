import requests
from requests.auth import HTTPBasicAuth
from ..common.settings import settings, IS_DRY_RUN
from ..common.utils import info_color


class GerritClient:
    def __init__(self):
        self.base_url = settings.GERRIT_URL.rstrip('/')
        self.user = settings.USER
        self.token = settings.API_TOKEN # 假设使用 HTTP Basic Auth 或 Bearer

    def score_change(self, change_id, score, label="Verified"):
        """
        给 Gerrit 变更打分
        """
        # Gerrit REST API 路径
        url = f"{self.base_url}/a/changes/{change_id}/revisions/current/review"
        
        info_color('info', f"正在连接 Gerrit: {self.base_url}")
        info_color('notes', f"准备给变更 {change_id} 打分: {label}={score}")
        
        payload = {
            "labels": {
                label: score
            }
        }

        # 真实环境请取消下面的注释
        # try:
        #     response = requests.post(url, json=payload, auth=(self.user, self.token))
        #     if response.status_code == 200:
        #         info_color('notes', "打分成功")
        #     else:
        #         info_color('error', f"打分失败: {response.status_code}")
        # except Exception as e:
        #     info_color('error', str(e))

        print(f"  -> [Mock] HTTP POST {url}")
        print(f"  -> [Mock] Payload: {payload}")

def get_gerrit_files(gerrit_url, auth, change_id, patchset_number=0):
    """
    调用 Gerrit API 获取指定 Patchset 的文件列表
    使用 /changes/{change-id}/revisions/{patchset-number}/files
    """
    # 确保 URL 格式正确，去除末尾斜杠
    base_url = gerrit_url.rstrip('/')
    if(patchset_number == 0):
        patchset_number = 'current'
    # 构建 API URL
    api_url = f"{base_url}/a/changes/{change_id}/revisions/{patchset_number}/files"

    if (IS_DRY_RUN):
        info_color('debug', f"正在获取 Patchset {patchset_number} 的文件列表 {api_url}")
        return ["gerrit_repo1:aa/path1.xml", "gerrit_repo1:bb/path2.xml", "gerrit_repo1:cc/path1.c" ]
    try:
        info_color('info', f"正在获取 Patchset {patchset_number} 的文件列表...")
        response = requests.get(api_url, auth=auth, timeout=10)
        
        if response.status_code == 404:
            info_color('error', f"未找到变更或 Patchset: {change_id} (Rev: {patchset_number})")
            return []
            
        response.raise_for_status()
        
        # Gerrit API 返回的 JSON 有时包含 XSRF 前缀 ")]}'"，但 requests.json() 通常能处理
        # 如果报错，可能需要手动去除 response.text 的前4个字符
        data = response.json()
        
        # 返回文件路径列表
        files = list(data.keys())
        info_color('notes', f"成功获取 {len(files)} 个变更文件")
        return files
        
    except requests.exceptions.RequestException as e:
        info_color('error', f"Gerrit API 请求失败: {e}")
        return []
    
def get_gerrit_change(gerrit_base_url, gerrit_username, gerrit_token, change_number, patch_id=None):
    """
    获取 Gerrit Change 的详细信息。
    
    参数:
        gerrit_base_url: Gerrit 基础 URL (例如: https://gerrit.example.com)
        gerrit_username: 用户名
        gerrit_token: HTTP 密码或 API Token
        change_number: Change 的编号 (数字)
        patch_id: 指定的 Patch Set 编号 (数字)。如果为 None，则使用当前最新的 Patch Set。
    
    返回:
        包含项目、分支、所有者和文件列表的字典
    """
    
    # 1. 基础 URL 处理，确保没有末尾的斜杠
    base_url = gerrit_base_url.rstrip('/')
    auth = (gerrit_username, gerrit_token)
    
    # 2. 第一步：获取 Change 的元数据
    # 如果指定了 patch_id，我们需要 ALL_REVISIONS 来查找对应的 revision hash
    # 如果没指定，只需要 CURRENT_REVISION
    option = "ALL_REVISIONS" if patch_id is not None else "CURRENT_REVISION"
    
    change_info_url = f"{base_url}/a/changes/{change_number}?o={option}"
    
    try:
        response = requests.get(change_info_url, auth=auth)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ 获取 Change 信息失败: {e}")
        return None

    # 处理 Gerrit 的 XSSI 保护前缀 ')]}'
    text_content = response.text
    if text_content.startswith(")]}'"):
        text_content = text_content[4:]
    
    try:
        change_data = json.loads(text_content)
    except json.JSONDecodeError:
        print("❌ JSON 解析失败")
        return None

    # 3. 提取基础信息
    project_name = change_data.get('project')
    branch_name = change_data.get('branch')
    # 注意：标准 API 返回的是 'owner' (单个对象)，这里为了适配你的 'owners' 列表格式做处理
    owner_name = change_data.get('owner', {}).get('name', 'Unknown')
    
    # 4. 确定目标 Revision ID (Commit Hash)
    target_revision_id = None
    
    if patch_id is None:
        # 情况 A: 使用当前 Patch
        target_revision_id = change_data.get('currentRevision')
    else:
        # 情况 B: 使用指定 Patch
        revisions = change_data.get('revisions', {})
        found = False
        for rev_hash, rev_info in revisions.items():
            if rev_info.get('number') == patch_id:
                target_revision_id = rev_hash
                found = True
                break
        
        if not found:
            print(f"❌ 未找到 Patch Set 编号: {patch_id}")
            return None

    if not target_revision_id:
        print("❌ 无法确定 Revision ID")
        return None

    # 5. 第二步：获取文件列表
    # 使用 /revisions/{revision-id}/files 接口
    files_url = f"{base_url}/a/changes/{change_number}/revisions/{target_revision_id}/files"
    
    try:
        files_response = requests.get(files_url, auth=auth)
        files_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ 获取文件列表失败: {e}")
        return None

    # 处理 XSSI 前缀
    files_text = files_response.text
    if files_text.startswith(")]}'"):
        files_text = files_text[4:]
        
    try:
        files_data = json.loads(files_text)
    except json.JSONDecodeError:
        print("❌ 文件列表 JSON 解析失败")
        return None

    # 6. 格式化文件列表
    # files_data 的格式是 { "path/to/file": { "status": "M", ... } }
    # 我们需要转换为 [ "project:path/to/file", ... ]
    formatted_files = []
    for file_path in files_data.keys():
        # 按照你的要求拼接 project:filepath
        formatted_files.append(f"{project_name}:{file_path}")

    # 7. 构建最终返回结果
    result = {
        "projects": [project_name],  # 按照要求返回列表
        "branch": branch_name,
        "owners": [owner_name],      # 按照要求返回列表
        "files": formatted_files
    }

    return result


def get_gerrit_topic_change(gerrit_base_url, gerrit_username, gerrit_token, change_number, patch_id=None):
    """
    获取 Gerrit Change 的详细信息。
    
    参数:
        gerrit_base_url: Gerrit 基础 URL (例如: https://gerrit.example.com)
        gerrit_username: 用户名
        gerrit_token: HTTP 密码或 API Token
        change_number: Change 的编号 (数字)
        patch_id: 指定的 Patch Set 编号 (数字)。如果为 None，则使用当前最新的 Patch Set。
    
    返回:
        包含项目、分支、所有者和文件列表的字典
    """
    
    # 1. 基础 URL 处理，确保没有末尾的斜杠
    base_url = gerrit_base_url.rstrip('/')
    auth = (gerrit_username, gerrit_token)
    
    # 2. 第一步：获取 Change 的元数据
    # 如果指定了 patch_id，我们需要 ALL_REVISIONS 来查找对应的 revision hash
    # 如果没指定，只需要 CURRENT_REVISION
    option = "ALL_REVISIONS" if patch_id is not None else "CURRENT_REVISION"
    
    change_info_url = f"{base_url}/a/changes/{change_number}?o={option}"
    
    try:
        response = requests.get(change_info_url, auth=auth)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ 获取 Change 信息失败: {e}")
        return None

    # 处理 Gerrit 的 XSSI 保护前缀 ')]}'
    text_content = response.text
    if text_content.startswith(")]}'"):
        text_content = text_content[4:]
    
    try:
        change_data = json.loads(text_content)
    except json.JSONDecodeError:
        print("❌ JSON 解析失败")
        return None

    # 3. 提取基础信息
    project_name = change_data.get('project')
    branch_name = change_data.get('branch')
    # 注意：标准 API 返回的是 'owner' (单个对象)，这里为了适配你的 'owners' 列表格式做处理
    owner_name = change_data.get('owner', {}).get('name', 'Unknown')
    
    # 4. 确定目标 Revision ID (Commit Hash)
    target_revision_id = None
    
    if patch_id is None:
        # 情况 A: 使用当前 Patch
        target_revision_id = change_data.get('currentRevision')
    else:
        # 情况 B: 使用指定 Patch
        revisions = change_data.get('revisions', {})
        found = False
        for rev_hash, rev_info in revisions.items():
            if rev_info.get('number') == patch_id:
                target_revision_id = rev_hash
                found = True
                break
        
        if not found:
            print(f"❌ 未找到 Patch Set 编号: {patch_id}")
            return None

    if not target_revision_id:
        print("❌ 无法确定 Revision ID")
        return None

    # 5. 第二步：获取文件列表
    # 使用 /revisions/{revision-id}/files 接口
    files_url = f"{base_url}/a/changes/{change_number}/revisions/{target_revision_id}/files"
    
    try:
        files_response = requests.get(files_url, auth=auth)
        files_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ 获取文件列表失败: {e}")
        return None

    # 处理 XSSI 前缀
    files_text = files_response.text
    if files_text.startswith(")]}'"):
        files_text = files_text[4:]
        
    try:
        files_data = json.loads(files_text)
    except json.JSONDecodeError:
        print("❌ 文件列表 JSON 解析失败")
        return None

    # 6. 格式化文件列表
    # files_data 的格式是 { "path/to/file": { "status": "M", ... } }
    # 我们需要转换为 [ "project:path/to/file", ... ]
    formatted_files = []
    for file_path in files_data.keys():
        # 按照你的要求拼接 project:filepath
        formatted_files.append(f"{project_name}:{file_path}")

    # 7. 构建最终返回结果
    result = {
        "projects": [project_name],  # 按照要求返回列表
        "branch": branch_name,
        "owners": [owner_name],      # 按照要求返回列表
        "files": formatted_files
    }

    return result

def post_gerrit_score(gerrit_base_url, gerrit_username, gerrit_token, change_number, patch_id=0, score=0, comment="default comment"):
    """
    给 Gerrit Change 打分 (Review)。
    
    参数:
        gerrit_base_url: Gerrit 基础 URL (例如: https://gerrit.example.com)
        gerrit_username: 用户名
        gerrit_token: HTTP 密码或 API Token
        change_number: Change 的编号 (数字)
        patch_id: 指定的 Patch Set 编号。如果是 0，则对当前最新的 Patch 打分。
        score: 打分值 (通常为 -1, 0, 1)。
               注意：Gerrit 默认标签通常是 Code-Review。
        comment: 打分时附带的注释内容。
    
    返回:
        布尔值: 成功返回 True，失败返回 False
    """
    
    base_url = gerrit_base_url.rstrip('/')
    auth = (gerrit_username, gerrit_token)
    
    # 1. 第一步：确定 Revision ID
    # 我们需要知道要打分的 patch 对应的 commit hash (revision id)
    revision_id = None
    
    # 决定查询参数
    if patch_id == 0:
        # 如果是 0，查询当前 revision
        option = "CURRENT_REVISION"
    else:
        # 如果指定了 patch_id，查询所有 revision 以便查找对应的 hash
        option = "ALL_REVISIONS"
        
    change_info_url = f"{base_url}/a/changes/{change_number}?o={option}"
    
    try:
        response = requests.get(change_info_url, auth=auth)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ 获取 Change 信息失败: {e}")
        return False

    # 处理 XSSI 前缀
    text_content = response.text
    if text_content.startswith(")]}'"):
        text_content = text_content[4:]
    
    try:
        change_data = json.loads(text_content)
    except json.JSONDecodeError:
        print("❌ JSON 解析失败")
        return False

    # 解析 Revision ID
    if patch_id == 0:
        revision_id = change_data.get('currentRevision')
    else:
        revisions = change_data.get('revisions', {})
        for rev_hash, rev_info in revisions.items():
            if rev_info.get('number') == patch_id:
                revision_id = rev_hash
                break
    
    if not revision_id:
        target_desc = f"Patch {patch_id}" if patch_id != 0 else "Current Patch"
        print(f"❌ 无法找到 {target_desc} 的 Revision ID。")
        return False

    # 2. 第二步：构造 Review 请求
    # API: PUT /a/changes/{change-id}/revisions/{revision-id}/review
    review_url = f"{base_url}/a/changes/{change_number}/revisions/{revision_id}/review"
    
    # 构造请求体
    # Gerrit 的 labels 通常是 "Code-Review"，但也可能是 "Verified"
    # 这里默认使用 "Code-Review"
    review_payload = {
        "labels": {
            "Code-Review": score
        },
        "message": comment
    }
    
    # 发送 PUT 请求
    # 注意：Gerrit REST API 发送 JSON 数据时，Content-Type 必须是 application/json
    try:
        put_response = requests.put(
            review_url, 
            auth=auth, 
            json=review_payload, # requests 库会自动处理 json 序列化和 headers
            headers={"Content-Type": "application/json"}
        )
        put_response.raise_for_status()
        
        print(f"✅ 打分成功！Change: {change_number}, Patch: {patch_id}, Score: {score}")
        return True
        
    except requests.exceptions.HTTPError as e:
        # 捕获具体的 HTTP 错误信息
        error_text = e.response.text
        if error_text.startswith(")]}'"):
            error_text = error_text[4:]
        print(f"❌ 打分失败 (HTTP {e.response.status_code}): {error_text}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 打分请求异常: {e}")
        return False
    
def post_gerrit_score_by_topic(gerrit_base_url, gerrit_username, gerrit_token, topic_name, score=1, comment="Auto-score via script"):
    """
    根据 Topic 字符串，给该 Topic 下所有 OPEN 状态的 Change 打分。
    
    参数:
        gerrit_base_url: Gerrit 基础 URL
        gerrit_username: 用户名
        gerrit_token: HTTP 密码或 API Token
        topic_name: Topic 名称 (字符串)
        score: 打分值 (-1, 0, 1)
        comment: 打分注释
    
    返回:
        字典: 包含成功和失败的数量统计
    """
    
    base_url = gerrit_base_url.rstrip('/')
    auth = (gerrit_username, gerrit_token)
    
    # --- 第一步：搜索 Topic 下的 OPEN Changes ---
    # 查询语法: topic:xxx status:open
    search_query = f"topic:{topic_name}+status:open"
    search_url = f"{base_url}/a/changes/?q={search_query}"
    
    print(f"🔍 正在搜索 Topic '{topic_name}' 下的 Open Changes...")
    
    try:
        search_response = requests.get(search_url, auth=auth)
        search_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ 搜索请求失败: {e}")
        return {"success": 0, "failed": 0}

    # 处理 XSSI 前缀
    search_text = search_response.text
    if search_text.startswith(")]}'"):
        search_text = search_text[4:]
    
    try:
        search_results = json.loads(search_text)
    except json.JSONDecodeError:
        print("❌ 搜索结果 JSON 解析失败")
        return {"success": 0, "failed": 0}

    if not search_results:
        print(f"ℹ️  Topic '{topic_name}' 下没有发现 Open 状态的 Change。")
        return {"success": 0, "failed": 0}

    print(f"✅ 找到 {len(search_results)} 个 Open Change，准备开始打分...")
    
    # --- 第二步：遍历并打分 ---
    success_count = 0
    failed_count = 0
    
    for change_summary in search_results:
        change_id = change_summary.get('id') # 完整 ID (如 I123...)
        change_num = change_summary.get('_number') # 数字 ID
        current_revision = change_summary.get('current_revision') # 搜索接口通常会直接返回 current_revision
        
        if not current_revision:
            print(f"⚠️  Change {change_num} 缺少 revision 信息，跳过。")
            failed_count += 1
            continue

        # 构造打分请求
        # API: PUT /a/changes/{change-id}/revisions/{revision-id}/review
        review_url = f"{base_url}/a/changes/{change_id}/revisions/{current_revision}/review"
        
        review_payload = {
            "labels": {
                "Code-Review": score
            },
            "message": comment
        }
        
        try:
            put_response = requests.put(
                review_url, 
                auth=auth, 
                json=review_payload,
                headers={"Content-Type": "application/json"}
            )
            put_response.raise_for_status()
            
            print(f"  ✅ Change {change_num}: 打分 {score} 成功")
            success_count += 1
            
        except requests.exceptions.HTTPError as e:
            error_text = e.response.text
            if error_text.startswith(")]}'"):
                error_text = error_text[4:]
            print(f"  ❌ Change {change_num}: 打分失败 - {error_text.strip()}")
            failed_count += 1
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Change {change_num}: 请求异常 - {e}")
            failed_count += 1

    return {"success": success_count, "failed": failed_count}

