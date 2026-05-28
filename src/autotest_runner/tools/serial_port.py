import logging

class SerialTool:
    """串口通信与日志抓取工具"""
    def __init__(self, port="/dev/ttyUSB0", baudrate=115200):
        self.port = port
        self.baudrate = baudrate

    def send_command(self, cmd):
        logging.info(f"📟 [Serial] 发送串口指令至 {self.port}: {cmd}")
        return "mock_response\nOK"
