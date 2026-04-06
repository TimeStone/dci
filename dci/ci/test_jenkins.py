import unittest
from unittest.mock import patch, MagicMock
# 这里根据你的真实路径调整导入
from your_module.jenkins_client import JenkinsClient  

class TestJenkinsClient(unittest.TestCase):

    def setUp(self):
        self.client = JenkinsClient(
            base_url="https://jenkins.test.com", 
            username="test_user", 
            token="test_token"
        )

    @patch('your_module.jenkins_client.requests.request')
    @patch.object(JenkinsClient, '_get_crumb')
    def test_trigger_job_with_params_success(self, mock_get_crumb, mock_request):
        """测试带参数触发 Jenkins 任务成功"""
        # 模拟 Crumb
        mock_get_crumb.return_value = {"Jenkins-Crumb": "abc12345"}
        
        # 模拟 HTTP 响应
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_request.return_value = mock_response
        
        params = {"BRANCH": "develop", "CLEAN": "true"}
        result = self.client.trigger_job("my-build-job", parameters=params)
        
        self.assertTrue(result)
        # 校验请求方法、URL 以及是否带上了 Crumb
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], 'POST')
        self.assertIn("Jenkins-Crumb", kwargs['headers'])

    @patch('your_module.jenkins_client.requests.request')
    def test_trigger_job_failed(self, mock_request):
        """测试触发 Jenkins 任务失败的情况"""
        # 模拟请求抛出异常
        mock_request.side_effect = Exception("Connection timed out")
        
        result = self.client.trigger_job("my-build-job")
        
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()