import logging
import subprocess
from pathlib import Path

class ADBTool:
    """ADB 设备通用控制工具"""
    def __init__(self, device_id=None):
        self.device_id = device_id
        self.cmd_prefix = ["adb"]
        if device_id:
            self.cmd_prefix.extend(["-s", device_id])

    def run_cmd(self, args, check=True, timeout=60):
        cmd = self.cmd_prefix + args
        logging.info(f"⚙️ [ADB] Executing: {' '.join(cmd)}")
        try:
            completed = subprocess.run(
                cmd,
                check=check,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return completed.stdout
        except FileNotFoundError as exc:
            raise RuntimeError("adb command not found. Please install Android platform-tools.") from exc
        except subprocess.CalledProcessError as exc:
            logging.error("ADB command failed: %s", exc.stderr or exc.stdout)
            if check:
                raise
            return exc.stdout or exc.stderr or ""

    def clear_app_data(self, package_name):
        return self.run_cmd(["shell", "pm", "clear", package_name])

    def push_file(self, src, dest):
        return self.run_cmd(["push", src, dest])

    def pull(self, remote_path, local_path):
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        return self.run_cmd(["pull", remote_path, str(local_path)], check=False, timeout=120)

    def dump_logcat(self, local_path):
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        output = self.run_cmd(["logcat", "-d"], check=False, timeout=60)
        local_path.write_text(output, encoding="utf-8", errors="replace")
        return local_path

    def screenshot(self, local_path):
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        remote = "/sdcard/autotest_runner_screenshot.png"
        self.run_cmd(["shell", "screencap", "-p", remote], check=False, timeout=20)
        self.pull(remote, local_path)
        self.run_cmd(["shell", "rm", "-f", remote], check=False, timeout=10)
        return local_path

    def bugreport(self, local_path):
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        return self.run_cmd(["bugreport", str(local_path)], check=False, timeout=300)

    def get_devices(self):
        output = self.run_cmd(["devices"], check=False, timeout=10)
        devices = []
        for line in output.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
        return devices

    def get_device_info(self, device_id):
        tool = ADBTool(device_id)
        return {
            "model": tool.run_cmd(["shell", "getprop", "ro.product.model"], check=False).strip(),
            "brand": tool.run_cmd(["shell", "getprop", "ro.product.brand"], check=False).strip(),
            "version": tool.run_cmd(["shell", "getprop", "ro.build.version.release"], check=False).strip(),
        }
