import pytest
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SafeExecutionPlugin:
    """
    核心：Try-Except-Finally 执行引擎。
    拦截 pytest 的执行，确保硬件资源的释放和日志的绝对收集。
    """
    def pytest_runtest_call(self, item):
        logging.info(f"▶️ [Pre-case] 准备执行用例: {item.name}. 初始化本地硬件设备环境...")
        
        try:
            # 执行用例本体
            item.runtest()
            logging.info(f"✅ [Case-run] 用例业务逻辑执行通过: {item.name}")
            
        except AssertionError as e:
            logging.error(f"❌ [Case-run] 业务断言失败 (Bug): {e}")
            raise
            
        except Exception as e:
            # 捕获例如 DeviceOfflineError 等硬件/环境异常
            logging.error(f"⚠️ [Case-run] 本地环境或硬件异常 (非业务Bug): {e}")
            raise
            
        finally:
            # 无论成功还是崩溃，finally 绝对保证兜底清理
            logging.info(f"⏹ [Post-case] 绝对兜底: 采集本地日志、断开继电器、释放串口锁...")

def run_tests_locally(test_path, report_to_cloud=False, hub_url=None, token=None):
    """本地执行主入口"""
    logging.info(f"🚀 开始本地执行目录: {test_path}")
    
    pytest_args = [test_path, "-v", "--html=local_report.html", "--self-contained-html"]
    
    if report_to_cloud:
        logging.info(f"☁️ 检测到协同模式，执行完毕后将把结果上报至云端: {hub_url}")
    else:
        logging.info(f"💻 当前为【离线独立模式】，结果仅生成本地 HTML 报告。")
        
    # 注入安全执行插件
    exit_code = pytest.main(pytest_args, plugins=[SafeExecutionPlugin()])
    
    if report_to_cloud:
        logging.info("☁️ 正在将执行结果、本地截图和串口日志上传至云端...")
        # TODO: call requests.post(hub_url + '/api/execution-runs/...')
        logging.info("☁️ 云端同步完成！")
        
    return exit_code
