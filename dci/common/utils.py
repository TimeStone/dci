import sys
import os
import random
import re
import fnmatch
import json

WARM_THEMES = [
    {
        "name": "Sunset Orange", # 夕阳橙
        "primary": '\033[38;2;255;160;60m',  # RGB 橙色
        "accent": '\033[38;2;255;200;100m',  # 浅黄
        "text": '\033[38;2;255;240;220m'     # 米白
    },
    {
        "name": "Cherry Pink", # 樱花粉
        "primary": '\033[38;2;255;105;180m', # RGB 热粉
        "accent": '\033[38;2;255;182;193m',  # 浅粉
        "text": '\033[38;2;255;228;225m'     # 雾白
    },
    {
        "name": "Golden Hour", # 黄金时刻
        "primary": '\033[38;2;218;165;32m',  # 金色
        "accent": '\033[38;2;255;215;0m',    # 亮金
        "text": '\033[38;2;255;250;205m'     # 柠檬绸
    },
    {
        "name": "Warm Red", # 暖红
        "primary": '\033[38;2;205;92;92m',   # 印度红
        "accent": '\033[38;2;240;128;128m',  # 亮珊瑚
        "text": '\033[38;2;255;230;230m'     # 雪白
    },
    {
        "name": "Cyber Warm", # 赛博暖色
        "primary": '\033[38;2;255;127;80m',  # 珊瑚橙
        "accent": '\033[38;2;255;165;79m',   # 橙红
        "text": '\033[38;2;255;245;238m'     # 花白
    }
]

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'  # 绿色：关键提示 (Notes)
    WARNING = '\033[93m'  # 橙色：警告 (Warn)
    FAIL = '\033[91m'     # 红色：错误 (Error)
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    CYAN = '\033[96m'       # 主色调：青色
    WHITE = '\033[97m'       # 辅助色：白色
    GRAY = '\033[38;2;255;245;238m'
    RESET = '\033[0m'

def info_color(type_: str, info: str):
    """
    根据类型输出带颜色的信息到控制台
    type: 'warn' (橙色), 'error' (红色), 'notes' (绿色), 'info' (青色)
    """
    color = Colors.ENDC
    prefix = ""

    if type_ == 'warn':
        color = Colors.WARNING
        prefix = "[WARNING]"
    elif type_ == 'error':
        color = Colors.FAIL
        prefix = "[ERROR]"
    elif type_ == 'notes':
        color = Colors.OKGREEN
        prefix = "[NOTES]"
    elif type_ == 'debug':
        color = Colors.GRAY
        prefix = "[DEBUG]"
    elif type_ == 'info':
        color = Colors.OKCYAN
        prefix = "[INFO]"
    else:
        # 默认行为
        print(info)
        return

    # 格式化输出： [PREFIX] 消息内容
    # 使用 sys.stderr 输出错误和警告，标准输出输出其他信息
    output_stream = sys.stderr if type_ in ['error', 'warn'] else sys.stdout
    print(f"{color}{Colors.BOLD}{prefix}{Colors.ENDC} {info}", file=output_stream)

def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    base_path = os.path.abspath(os.path.dirname(__file__))
    # 假设 resource 文件夹在 dci 根目录下，需要回退两级
    return os.path.join(base_path, '..', 'resource', relative_path)

def print_banner():
    """加载并打印 Banner，每次随机应用一种温暖色调"""
    banner_file = get_resource_path('banner.txt')
    
    # 1. 随机选择一个主题
    theme = random.choice(WARM_THEMES)
    primary_color = theme["primary"]
    accent_color = theme["accent"]
    text_color = theme["text"]
    
    try:
        with open(banner_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.splitlines()
        
        if lines:
            # 2. 使用随机颜色打印
            # 顶部边框
            print(f"{primary_color}{Colors.BOLD}{lines[0]}{Colors.RESET}")
            
            # 中间内容
            for line in lines[1:]:
                print(f"{primary_color}{line}{Colors.RESET}")
            
            # 底部文字信息
            print(f"{accent_color}{Colors.BOLD}   DCI System v1.0.0  //  Distributed CI Orchestrator{Colors.RESET}")
            print(f"{text_color}   > 状态: 就绪  |  模式: 智能触发  |  连接: 安全{Colors.RESET}")
            
    except FileNotFoundError:
        print(f"{accent_color}[WARNING] Banner file not found{Colors.RESET}")
        print("DCI System v1.0.0")


def matches_pattern(file_path, pattern):
    """
    判断文件路径是否匹配给定的模式
    支持正则表达式，也支持简单的通配符逻辑
    """
    try:
        # 尝试直接使用正则匹配
        if re.match(pattern, file_path):
            return True
        return False
    except re.error:
        # 如果正则本身有误，尝试 fnmatch (shell 风格通配符)
        return fnmatch.fnmatch(file_path, pattern)


def load_json_file(path, description):
    """通用 JSON 加载函数，包含错误处理"""
    try:
        if not os.path.exists(path):
            info_color('error', f"文件不存在: {path}")
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        info_color('error', f"JSON 解析失败 ({description}): {e}")
        return None
    except Exception as e:
        info_color('error', f"读取文件失败 ({description}): {e}")
        return None