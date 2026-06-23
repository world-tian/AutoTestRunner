import logging

class RelayTool:
    """继电器电源控制工具 (例如通过 HTTP 或串口发送指令断电重启)"""
    def __init__(self, ip_address):
        self.ip = ip_address

    def power_off(self, port=1):
        logging.info(f"🔌 [Relay] 发送断电指令 -> {self.ip} 端口:{port}")
        return True

    def power_on(self, port=1):
        logging.info(f"🔌 [Relay] 发送上电指令 -> {self.ip} 端口:{port}")
        return True

    def restart(self, port=1, delay_sec=3):
        self.power_off(port)
        logging.info(f"⏳ [Relay] 等待 {delay_sec} 秒...")
        self.power_on(port)
