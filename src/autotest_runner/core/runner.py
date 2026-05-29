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
    
    # 确保 reports 目录存在并有权限
    try:
        os.makedirs(reports_dir, exist_ok=True)
    except Exception as e:
        logging.warning(f"⚠️ 无法创建报告目录 {reports_dir}: {e}, 回退到 /tmp")
        reports_dir = "/tmp/autotest_reports"
        os.makedirs(reports_dir, exist_ok=True)
        
    report_name = os.path.join(reports_dir, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
    
    pytest_args = target_paths + ["-v", f"--html={report_name}", "--self-contained-html"]
    
    # pytest 内部的插件在某些系统环境下打开文件时可能遇到 PermissionError
    # 这里通过捕获外层异常或确保文件可写来防御
    try:
        # 预先创建一个空文件并赋予权限
        with open(report_name, 'w') as f:
            pass
        os.chmod(report_name, 0o666)
    except Exception as e:
        logging.warning(f"⚠️ 预先创建报告文件失败: {e}")
    
    try:
        exit_code = pytest.main(pytest_args, plugins=[SafeExecutionPlugin()])
        logging.info(f"📊 本地报告已生成: {report_name}")
        return exit_code
    except Exception as e:
        logging.error(f"❌ pytest 执行过程中发生异常: {e}")
        return 1
