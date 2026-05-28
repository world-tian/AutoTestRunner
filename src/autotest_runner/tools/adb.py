import logging
import subprocess

class ADBTool:
    """ADB 设备通用控制工具"""
    def __init__(self, device_id=None):
        self.device_id = device_id
        self.cmd_prefix = ["adb"]
        if device_id:
            self.cmd_prefix.extend(["-s", device_id])

    def run_cmd(self, args):
        cmd = self.cmd_prefix + args
        logging.info(f"⚙️ [ADB] Executing: {' '.join(cmd)}")
        # 真实环境中这里使用 subprocess.run，这里做个模拟打印
        return "mock_success"

    def clear_app_data(self, package_name):
        return self.run_cmd(["shell", "pm", "clear", package_name])

    def push_file(self, src, dest):
        return self.run_cmd(["push", src, dest])
