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
    
    # 确保 reports 目录存在
    os.makedirs("reports", exist_ok=True)
    report_name = f"reports/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    
    pytest_args = target_paths + ["-v", f"--html={report_name}", "--self-contained-html"]
    
    exit_code = pytest.main(pytest_args, plugins=[SafeExecutionPlugin()])
    
    logging.info(f"📊 本地报告已生成: {report_name}")
    return exit_code
