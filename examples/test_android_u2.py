from autotest_runner import autotest
from autotest_runner.tools import U2Tool
import pytest
import time

@autotest(case_id="TC-ANDROID-001", title="安卓UI自动化-设置页测试", priority="P0")
def test_android_settings():
    """
    使用 uiautomator2 操作安卓设备的示例
    确保已经使用数据线连接安卓设备，或使用模拟器，并且设备上已开启 USB 调试。
    """
    # 1. 初始化 U2Tool，不传参数时将自动寻找 USB 连接的设备或环境变量 AUTOTEST_DEVICE_ID
    try:
        u2 = U2Tool()
    except (ImportError, RuntimeError, Exception) as exc:
        pytest.skip(f"Android UI environment is not available: {exc}")
    
    # 2. 启动 Android 设置应用
    u2.app_start("com.android.settings")
    time.sleep(2)
    
    # 3. 使用原始的 uiautomator2 API 获取设备信息
    device_info = u2.device.info
    print(f"当前设备信息: {device_info}")
    
    # 4. 滑动屏幕 (使用原始 device 对象)
    u2.device.swipe_ext("up", scale=0.8)
    
    # 5. 截图并保存
    u2.screenshot("settings_screen.jpg")
    
    # 6. 关闭应用
    u2.app_stop("com.android.settings")
