from autotest_runner import autotest

@autotest(case_id="TC-001", req_id="REQ-101", title="测试智能插座继电器通断", priority="P0")
def test_relay_power_cycle():
    """
    模拟一个本地硬件测试
    """
    print(">> 正在发送指令关闭继电器...")
    # 假设断言继电器状态
    assert True
    
@autotest(case_id="TC-002", title="测试设备意外断网", priority="P1")
def test_device_offline():
    print(">> 模拟设备断开...")
    raise Exception("DeviceOfflineError: 串口连接丢失")
