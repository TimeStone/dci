#!/bin/bash

# 设置颜色变量，让输出更清晰
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 定义测试的标题
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   DCI Tool Automated Test Suite        ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 记录测试结果的计数器
TESTS_PASSED=0
TESTS_FAILED=0

# 定义一个辅助函数来运行命令并检查结果
run_test() {
    local test_name="$1"
    local command="$2"
    
    echo -e "${YELLOW}>>> 测试项: ${test_name}${NC}"
    echo -e "${GREEN}执行命令: ${command}${NC}"
    
    # 执行命令
    eval "$command"
    
    # 检查上一条命令的退出状态码 ($?)
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 测试通过: ${test_name}${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ 测试失败: ${test_name}${NC}"
        ((TESTS_FAILED++))
    fi
    
    echo "----------------------------------------"
    echo ""
}

# 1. 测试 --version
# 预期：输出版本号 1.0.0 并正常退出
run_test "检查版本号 (--version)" "python -m dci --version"

# 2. 测试 --help (全局)
# 预期：显示帮助菜单，包含 trigger 和 score 命令
run_test "全局帮助信息 (--help)" "python -m dci --help"

# 3. 测试 trigger --help
# 预期：显示 trigger 子命令的特定帮助，包含 --config 和 --change-id 选项
run_test "Trigger 命令帮助 (trigger --help)" "python -m dci trigger --help"

# 4. 测试 score --help
# 预期：显示 score 子命令的特定帮助
run_test "Score 命令帮助 (score --help)" "python -m dci score --help"

# 5. 模拟触发测试 (Dry Run)
# 预期：解析 JSON 配置，模拟触发流水线，但不发送真实网络请求
# 注意：这里假设 conf/conf_ci_trigger.json 文件存在
run_test "模拟触发流水线 (Dry Run)" "python -m dci trigger --config ./conf/conf_ci_trigger.json --change-id 123456 --dry-run"

# 6. 模拟打分测试
# 预期：模拟发送打分请求
run_test "模拟打分操作" "python -m dci score --change-id 123456 --score 1 --label Verified"

# 打印最终统计结果
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}           测试执行摘要                 ${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "通过: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "失败: ${RED}${TESTS_FAILED}${NC}"

# 如果有失败的测试，脚本以错误代码退出
if [ $TESTS_FAILED -gt 0 ]; then
    exit 1
fi