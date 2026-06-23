import logging
import os

try:
    import uiautomator2 as u2
except ImportError:
    u2 = None

class U2Tool:
    """
    Android 自动化测试工具类，基于 openatx/uiautomator2
    """
    def __init__(self, serial=None):
        """
        初始化 uiautomator2 设备连接
        :param serial: 设备的序列号 (如 'emulator-5554') 或 IP (如 '192.168.1.10')。
                       如果为 None，优先读取环境变量 AUTOTEST_DEVICE_ID，否则连接默认设备。
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        if u2 is None:
            self.logger.error("未安装 uiautomator2。请运行 'pip install uiautomator2' 进行安装。")
            raise ImportError("uiautomator2 not installed")

        if not serial:
            serial = os.getenv("AUTOTEST_DEVICE_ID")

        try:
            self.d = u2.connect(serial)
            self.logger.info(f"✅ 成功连接 Android 设备: {self.d.info.get('model', 'Unknown')} (Serial: {self.d.serial})")
        except Exception as e:
            self.logger.error(f"❌ 无法连接 Android 设备 (Serial/IP: {serial}): {e}")
            raise

    @property
    def device(self):
        """
        返回原始的 uiautomator2 Device 对象，方便直接调用 u2 的原生 API
        """
        return self.d

    def app_start(self, package_name):
        """
        启动指定的应用程序
        """
        self.logger.info(f"启动应用: {package_name}")
        self.d.app_start(package_name)

    def app_stop(self, package_name):
        """
        停止指定的应用程序
        """
        self.logger.info(f"停止应用: {package_name}")
        self.d.app_stop(package_name)
        
    def click(self, text=None, resourceId=None, description=None, class_name=None):
        """
        快速点击封装
        """
        selector = {}
        if text: selector['text'] = text
        if resourceId: selector['resourceId'] = resourceId
        if description: selector['description'] = description
        if class_name: selector['className'] = class_name
        
        self.logger.info(f"尝试点击元素: {selector}")
        self.d(**selector).click()
        
    def screenshot(self, filename="screenshot.jpg"):
        """
        截图
        """
        self.logger.info(f"设备截图并保存为: {filename}")
        self.d.screenshot(filename)
