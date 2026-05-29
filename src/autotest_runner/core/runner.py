import subprocess
import sys
import os
import logging
from datetime import datetime

# 尝试加载全局环境变量配置
try:
    from dotenv import load_dotenv
    # 优先加载当前目录的 .env，如果没有则尝试加载家目录下的全局配置
    if os.path.exists(".env"):
        load_dotenv(".env")
    elif os.path.exists(os.path.expanduser("~/.autotest_env")):
        load_dotenv(os.path.expanduser("~/.autotest_env"))
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_tests_locally(target_paths, report_to_cloud=False, hub_url=None, token=None):
    if isinstance(target_paths, str):
        target_paths = [target_paths]
        
    logging.info(f"🚀 本地执行目标: {target_paths}")
    
    # 从全局环境变量获取工作目录，如果未配置则使用当前绝对路径
    global_workspace = os.getenv("AUTOTEST_WORKSPACE")
    if global_workspace and os.path.exists(global_workspace):
        abs_cwd = os.path.abspath(global_workspace)
        logging.info(f"📁 使用全局配置的工作目录: {abs_cwd}")
    else:
        abs_cwd = os.path.abspath(os.getcwd())
        logging.info(f"📁 使用当前工作目录: {abs_cwd}")
        
    reports_dir = os.path.join(abs_cwd, "reports")
    
    # 彻底解决 MacOS Sandbox/SIP 导致的 Operation not permitted 权限问题
    test_file = os.path.join(reports_dir, ".test_write")
    try:
        os.makedirs(reports_dir, exist_ok=True)
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
    except Exception as e:
        logging.warning(f"⚠️ 当前目录无写入权限 ({e})，报告将重定向至 /tmp/autotest_reports")
        reports_dir = "/tmp/autotest_reports"
        os.makedirs(reports_dir, exist_ok=True)
        
    report_name = os.path.join(reports_dir, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
    
    # 改为使用 python -m pytest 直接在指定目录下启动，满足用户的习惯
    pytest_args = [sys.executable, "-m", "pytest"] + target_paths + ["-v", f"--html={report_name}", "--self-contained-html", "-p", "no:cacheprovider"]
    
    try:
        logging.info(f"⚙️ 拉起子进程执行命令: {' '.join(pytest_args)}")
        process = subprocess.run(pytest_args, cwd=abs_cwd)
        logging.info(f"📊 本地报告已生成: {report_name}")
        return process.returncode
    except Exception as e:
        logging.error(f"❌ pytest 执行过程中发生异常: {e}")
        return 1
