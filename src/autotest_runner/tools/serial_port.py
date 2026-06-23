import logging
import re
import threading
import time
from pathlib import Path

class SerialTool:
    """串口通信与日志抓取工具"""
    def __init__(self, port="/dev/ttyUSB0", baudrate=115200, timeout=10):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial = None
        self._capture_thread = None
        self._capture_running = False
        self._log_lines = []
        self._lock = threading.Lock()
        self._log_file = None

    def open(self):
        if self._serial:
            return self._serial
        try:
            import serial
        except ImportError as exc:
            raise RuntimeError("pyserial is required when serial.enabled=true") from exc

        self._serial = serial.Serial(
            self.port,
            self.baudrate,
            timeout=0.2,
        )
        logging.info("📟 [Serial] 已打开串口 %s @ %s", self.port, self.baudrate)
        return self._serial

    def close(self):
        self.stop_capture()
        if self._serial:
            self._serial.close()
            self._serial = None

    def send_command(self, cmd):
        serial_conn = self.open()
        payload = cmd if isinstance(cmd, bytes) else str(cmd).encode("utf-8")
        if not payload.endswith(b"\n"):
            payload += b"\n"
        logging.info("📟 [Serial] 发送串口指令至 %s: %s", self.port, cmd)
        serial_conn.write(payload)
        serial_conn.flush()
        return True

    def expect(self, pattern, timeout=None):
        deadline = time.time() + float(timeout or self.timeout)
        regex = re.compile(pattern)
        start = self.mark()
        while time.time() < deadline:
            if regex.search(self.get_log_since(start)):
                return True
            time.sleep(0.1)
        return False

    def start_capture(self, log_file):
        self.open()
        self._log_file = Path(log_file)
        self._log_file.parent.mkdir(parents=True, exist_ok=True)
        self._capture_running = True
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()
        logging.info("📟 [Serial] 开始持续采集日志: %s", self._log_file)

    def stop_capture(self):
        self._capture_running = False
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2)
        self._capture_thread = None

    def mark(self):
        with self._lock:
            return len(self._log_lines)

    def get_log_since(self, offset):
        with self._lock:
            return "".join(self._log_lines[int(offset):])

    def find_patterns_since(self, offset, patterns):
        text = self.get_log_since(offset)
        matched = []
        for pattern in patterns or []:
            if re.search(pattern, text):
                matched.append(pattern)
        return matched

    def list_ports(self):
        try:
            from serial.tools import list_ports
        except ImportError:
            return []
        return [port.device for port in list_ports.comports()]

    def _capture_loop(self):
        while self._capture_running:
            try:
                if not self._serial:
                    self.open()
                raw = self._serial.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="replace")
                with self._lock:
                    self._log_lines.append(line)
                if self._log_file:
                    with self._log_file.open("a", encoding="utf-8") as log:
                        log.write(line)
            except Exception as exc:
                message = f"[SerialCaptureError] {exc}\n"
                logging.warning("📟 [Serial] 采集异常: %s", exc)
                with self._lock:
                    self._log_lines.append(message)
                if self._log_file:
                    with self._log_file.open("a", encoding="utf-8") as log:
                        log.write(message)
                time.sleep(1)
