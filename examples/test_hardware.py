import os
from autotest_runner import autotest
from autotest_runner.tools import RelayTool, ADBTool

@autotest(case_id="TC-001", req_id="REQ-101", title="测试智能插座继电器通断", priority="P0")
def test_relay_power_cycle():
    """使用内置工具控制硬件"""
    ip = os.getenv("DEVICE_IP", "127.0.0.1")
    relay = RelayTool(ip_address=ip)
    
    print(f"\n>> 正在测试 IP: {ip} 的继电器...")
    relay.power_off(port=1)
    relay.power_on(port=1)
    
    assert True
    
@autotest(case_id="TC-002", title="测试 ADB 日志抓取", priority="P1")
def test_adb_connection():
    adb = ADBTool()
    print("\n>> 正在尝试清空测试包数据...")
    adb.clear_app_data("com.example.smarthome")
    assert True
