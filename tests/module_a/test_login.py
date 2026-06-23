import time
import logging

def test_login_success(setup_test_env):
    logging.info("Running test_login_success")
    time.sleep(1)
    assert True

def test_login_failure(setup_test_env):
    logging.info("Running test_login_failure")
    time.sleep(1)
    # 模拟失败或者跳过
    assert True
