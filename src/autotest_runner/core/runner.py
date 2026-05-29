import pytest
import sys
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SafeExecutionPlugin:
    def pytest_runtest_call(self, item):
        logging.info(f"▶️ [Pre-case] 准备执行: {item.nodeid}")
        try:
            item.runtest()
            logging.info(f"✅ [Case-run] 执行通过: {item.nodeid}")
        except AssertionError as e:
            logging.error(f"❌ [Case-run] 断言失败: {e}")
            raise
        except Exception as e:
            logging.error(f"⚠️ [Case-run] 异常: {e}")
            raise
        finally:
            logging.info(f"⏹ [Post-case] 兜底清理资源...")

def run_tests_locally(target_paths, report_to_cloud=False, hub_url=None, token=None):
    if isinstance(target_paths, str):
        target_paths = [target_paths]
        
    logging.info(f"🚀 本地执行目标: {target_paths}")
    
    # 获取绝对路径，避免在不同 cwd 下产生权限/路径问题
    abs_cwd = os.path.abspath(os.getcwd())
    reports_dir = os.path.join(abs_cwd, "reports")
    
    # 彻底解决 MacOS Sandbox/SIP 导致的 Operation not permitted 权限问题
    # 如果是在 Agent 进程（可能是系统服务）中拉起，写入受保护目录会被拒绝，直接换到 /tmp
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
    
    pytest_args = target_paths + ["-v", f"--html={report_name}", "--self-contained-html"]
    
    try:
        exit_code = pytest.main(pytest_args, plugins=[SafeExecutionPlugin()])
        logging.info(f"📊 本地报告已生成: {report_name}")
        return exit_code
    except Exception as e:
        logging.error(f"❌ pytest 执行过程中发生异常: {e}")
        return 1
