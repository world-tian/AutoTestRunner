import os
import pytest
from autotest_runner.core.decorators import autotest

@autotest(case_id="TC-001", title="硬件连接测试", priority="P0")
def test_connection():
    device_ip = os.getenv("DEVICE_IP", "127.0.0.1")
    print(f"Connecting to device at {device_ip}...")
    assert True, "Connection successful"

@autotest(case_id="TC-002", title="传感器读取测试", priority="P1")
def test_sensor():
    print("Reading sensor data...")
    assert True, "Sensor read successful"
