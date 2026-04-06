import unittest
from unittest.mock import patch, MagicMock
# 这里根据你的真实路径调整导入
from your_module.gerrit_client import GerritClient  

class TestGerritClient(unittest.TestCase):

    def setUp(self):
        # 实例化时传入假数据，避免依赖真实 settings
        self.client = GerritClient(
            base_url="https://gerrit.test.com", 
            username="test_user", 
            token="test_token"
        )

    @patch('your_module.gerrit_client.requests.request')
    def test_get_gerrit_topic_change_success(self, mock_request):
        """测试根据 Topic 成功获取 Open Changes"""
        # 模拟 HTTP 响应
        mock_response = MagicMock()
        mock_response.text = ")]}'\n" + '[{"id": "I123", "_number": 123, "status": "NEW"}]'
        mock_request.return_value = mock_response
        
        result = self.client.get_gerrit_topic_change("feature-abc")
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['_number'], 123)
        mock_request.assert_called_once()

    @patch.object(GerritClient, 'get_gerrit_topic_change')
    @patch('your_module.gerrit_client.requests.request')
    def test_get_gerrit_topic_files(self, mock_request, mock_get_topic):
        """测试获取 Topic 的所有文件改动"""
        # 1. 模拟上一步 topic 变更的返回
        mock_get_topic.return_value = [
            {"_number": 123, "project": "repo1", "current_revision": "rev123"}
        ]
        
        # 2. 模拟请求 revisions/files 接口的返回
        mock_response = MagicMock()
        mock_response.text = ")]}'\n" + '{"path/to/file1.py": {}, "path/to/file2.py": {}}'
        mock_request.return_value = mock_response
        
        result = self.client.get_gerrit_topic_files("feature-abc")
        
        # 验证返回列表长度和格式
        self.assertEqual(len(result), 2)
        self.assertIn("repo1:path/to/file1.py", result)
        self.assertIn("repo1:path/to/file2.py", result)

if __name__ == '__main__':
    unittest.main()