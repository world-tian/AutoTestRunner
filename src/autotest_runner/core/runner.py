import pytest
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SafeExecutionPlugin:
    def pytest_runtest_call(self, item):
        logging.info(f"▶️ [Pre-case] 准备执行: {item.name}")
        try:
            item.runtest()
            logging.info(f"✅ [Case-run] 执行通过: {item.name}")
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
    
    pytest_args = target_paths + ["-v", "--html=local_report.html", "--self-contained-html"]
    
    exit_code = pytest.main(pytest_args, plugins=[SafeExecutionPlugin()])
    return exit_code
