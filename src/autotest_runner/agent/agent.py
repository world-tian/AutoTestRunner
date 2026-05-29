"""AutoTestRunner Agent - 执行 Agent"""
import os
import sys
import json
import time
import platform
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

import requests
from threading import Thread

from autotest_runner.tools.adb import ADBTool
from autotest_runner.tools.serial_port import SerialTool

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutoTestAgent:
    """执行 Agent"""
    
    def __init__(
        self,
        server_url: str,
        agent_name: str = None,
        heartbeat_interval: int = 10
    ):
        self.server_url = server_url.rstrip('/')
        self.agent_name = agent_name or f"Agent-{platform.node()}"
        self.heartbeat_interval = heartbeat_interval
        self.agent_id: Optional[str] = None
        self.running = False
        self.heartbeat_thread: Optional[Thread] = None
        self.execution_thread: Optional[Thread] = None
        
        # 设备管理
        self.adb_tool = ADBTool()
        self.serial_tool = SerialTool()
        self.connected_devices: List[Dict[str, Any]] = []
        
        # 任务队列
        self.pending_tasks: List[Dict[str, Any]] = []
        
        logger.info(f"AutoTest Agent initialized: {self.agent_name}")
        logger.info(f"  Server: {self.server_url}")
    
    def start(self):
        """启动 Agent"""
        logger.info("Starting AutoTest Agent...")
        self.running = True
        
        # 启动心跳线程
        self.heartbeat_thread = Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        
        # 启动执行线程
        self.execution_thread = Thread(target=self._execution_loop, daemon=True)
        self.execution_thread.start()
        
        logger.info("AutoTest Agent started successfully")
    
    def stop(self):
        """停止 Agent"""
        logger.info("Stopping AutoTest Agent...")
        self.running = False
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join()
        if self.execution_thread and self.execution_thread.is_alive():
            self.execution_thread.join()
        logger.info("AutoTest Agent stopped")
    
    def _discover_devices(self) -> List[Dict[str, Any]]:
        """发现本地设备"""
        devices = []
        
        try:
            # 发现 Android 设备
            android_devices = self.adb_tool.get_devices()
            for device in android_devices:
                device_info = self.adb_tool.get_device_info(device)
                devices.append({
                    "device_id": device,
                    "device_type": "android",
                    "name": device_info.get("model", device),
                    "manufacturer": device_info.get("brand"),
                    "model": device_info.get("model"),
                    "os_version": device_info.get("version"),
                    "status": "online",
                    "capabilities": ["adb"]
                })
        except Exception as e:
            logger.warning(f"Failed to discover Android devices: {e}")
        
        try:
            # 发现串口设备
            serial_ports = self.serial_tool.list_ports()
            for port in serial_ports:
                devices.append({
                    "device_id": port,
                    "device_type": "serial",
                    "name": port,
                    "status": "online",
                    "capabilities": ["serial"]
                })
        except Exception as e:
            logger.warning(f"Failed to discover serial devices: {e}")
        
        self.connected_devices = devices
        return devices
    
    def _heartbeat_loop(self):
        """心跳循环"""
        while self.running:
            try:
                self._send_heartbeat()
            except Exception as e:
                logger.error(f"Heartbeat failed: {e}")
            
            time.sleep(self.heartbeat_interval)
    
    def _send_heartbeat(self):
        """发送心跳"""
        # 发现设备
        devices = self._discover_devices()
        
        # 构建请求
        data = {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "status": "online",
            "health_score": 100,
            "devices": devices
        }
        
        # 发送请求
        url = f"{self.server_url}/api/agents/{self.agent_id or 'register'}/heartbeat"
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=5)
            response.raise_for_status()
            result = response.json()
            
            # 更新 agent_id
            if result.get("agent_id") and not self.agent_id:
                self.agent_id = result["agent_id"]
                logger.info(f"Registered with server, agent_id: {self.agent_id}")
            
            # 获取任务
            if "tasks" in result:
                self.pending_tasks.extend(result["tasks"])
                if result["tasks"]:
                    logger.info(f"Received {len(result['tasks'])} new tasks")
            
        except requests.RequestException as e:
            logger.error(f"Failed to send heartbeat: {e}")
            # 第一次失败时尝试不带 agent_id 注册
            if not self.agent_id and isinstance(e, requests.HTTPError):
                self.agent_id = None
    
    def _execution_loop(self):
        """执行循环"""
        while self.running:
            try:
                # 处理待执行任务
                if self.pending_tasks:
                    task = self.pending_tasks.pop(0)
                    self._execute_task(task)
            except Exception as e:
                logger.error(f"Execution loop error: {e}")
            
            time.sleep(1)
    
    def _execute_task(self, task: Dict[str, Any]):
        """执行任务"""
        task_id = task.get("task_id")
        run_id = task.get("run_id")
        device_id = task.get("device_id")
        config = task.get("config", {})
        
        working_dir = config.get("working_dir")
        test_command = config.get("test_command")
        
        logger.info(f"Executing task {task_id} for run {run_id}")
        logger.info(f"  Working Dir: {working_dir}")
        logger.info(f"  Command: {test_command}")
        
        try:
            # 更新任务状态为运行中
            self._update_task_status(task_id, "running")
            
            if not test_command:
                raise ValueError("Test command is not specified (e.g. pytest tests/)")
                
            # 执行实际测试
            logger.info(f"Executing test on device {device_id}...")
            
            import subprocess
            
            # 使用 subprocess 执行命令
            env = os.environ.copy()
            if device_id:
                env["AUTOTEST_DEVICE_ID"] = device_id
            
            # 使用全局配置的工作目录优先，如果未配置，再使用 working_dir 或当前目录
            global_workspace = os.getenv("AUTOTEST_WORKSPACE")
            if global_workspace and os.path.exists(global_workspace):
                cwd = global_workspace
            else:
                cwd = working_dir if working_dir and os.path.exists(working_dir) else os.getcwd()
            
            # 自动将 pytest 替换为 python -m pytest，以满足用户在特定目录直接启动的习惯
            if test_command and test_command.startswith("pytest"):
                test_command = test_command.replace("pytest", "python -m pytest", 1)
            elif test_command and test_command.startswith("autotest-runner run"):
                # 如果是 autotest-runner run，也可以转换为 python -m pytest (这里只是尽量兼容)
                pass
                
            logger.info(f"Running command: {test_command} in {cwd}")
            
            output = []
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            initial_logs = [
                f"[{current_time}] 🚀 接收到云端测试任务下发 (Task ID: {task_id})\n",
                f"[{current_time}] 🎯 选中执行节点: {self.agent_name} (ID: {self.agent_id})\n",
                f"[{current_time}] 📁 准备工作目录: {cwd}\n",
                f"[{current_time}] ⚙️ 开始拉起执行命令: {test_command}\n",
                "-" * 60 + "\n"
            ]
            output.extend(initial_logs)
            self._append_task_log(task_id, "".join(initial_logs))
            
            process = subprocess.Popen(
                test_command,
                shell=True,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            log_buffer = []
            last_flush_time = time.time()
            
            for line in process.stdout:
                logger.info(f"[Task {task_id}] {line.strip()}")
                output.append(line)
                log_buffer.append(line)
                
                if time.time() - last_flush_time > 2.0 or len(log_buffer) > 20:
                    self._append_task_log(task_id, "".join(log_buffer))
                    log_buffer = []
                    last_flush_time = time.time()
                    
            if log_buffer:
                self._append_task_log(task_id, "".join(log_buffer))
                
            process.wait()
            
            finish_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            finish_logs = ["-" * 60 + "\n"]
            output.extend(finish_logs)
            self._append_task_log(task_id, "".join(finish_logs))
            if process.returncode == 0:
                result_status = "Success"
                error_msg = None
                logger.info(f"Task {task_id} completed successfully")
                output.append(f"[{finish_time}] ✅ 执行命令顺利完成，退出码: 0\n")
            else:
                result_status = "Failed"
                error_msg = f"Command exited with code {process.returncode}"
                logger.error(f"Task {task_id} failed: {error_msg}")
                output.append(f"[{finish_time}] ❌ 执行命令发生异常，退出码: {process.returncode}\n")
            
            full_output = "".join(output)
            
            # 寻找生成的 HTML 报告并回传内容
            html_report = None
            import re
            report_match = re.search(r"本地报告已生成:\s*([^\n]+)", full_output)
            if report_match:
                latest_report_file = report_match.group(1).strip()
                try:
                    with open(latest_report_file, 'r', encoding='utf-8') as f:
                        html_report = f.read()
                    output.append(f"[{finish_time}] 📊 成功读取本地 HTML 报告并准备上报云端: {os.path.basename(latest_report_file)}\n")
                except Exception as e:
                    logger.error(f"Failed to read html report: {e}")
                    output.append(f"[{finish_time}] ⚠️ 读取本地 HTML 报告失败: {e}\n")
            else:
                output.append(f"[{finish_time}] ⚠️ 未能在日志中找到本地 HTML 报告路径\n")
            
            full_output = "".join(output)
            
            # 更新任务状态为完成
            self._update_task_status(
                task_id, 
                "completed" if process.returncode == 0 else "failed", 
                result=full_output,
                error_message=error_msg,
                html_report=html_report
            )
            
        except Exception as e:
            logger.error(f"Task {task_id} failed with exception: {e}")
            self._update_task_status(task_id, "failed", error_message=str(e))
    
    def _append_task_log(self, task_id: str, log_data: str):
        """实时追加日志"""
        if not log_data:
            return
        try:
            url = f"{self.server_url}/api/execution-queue/{task_id}/log"
            requests.post(url, json={"log": log_data}, timeout=5)
        except Exception as e:
            logger.error(f"Failed to append task log: {e}")

    def _update_task_status(
        self,
        task_id: str,
        status: str,
        result: str = None,
        error_message: str = None,
        html_report: str = None
    ):
        """更新任务状态"""
        try:
            if status == "running":
                url = f"{self.server_url}/api/execution-queue/{task_id}/start"
                requests.post(url)
            elif status in ["completed", "failed"]:
                url = f"{self.server_url}/api/execution-queue/{task_id}/complete"
                payload = {
                    "result": result,
                    "error_message": error_message,
                    "success": status == "completed"
                }
                if html_report:
                    payload["html_report"] = html_report
                requests.post(url, json=payload)
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AutoTestRunner Agent")
    parser.add_argument(
        "--server",
        default=os.environ.get("AUTOTEST_SERVER", "http://localhost:8000"),
        help="AutoTestHub server URL"
    )
    parser.add_argument(
        "--name",
        help="Agent name"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="Heartbeat interval in seconds"
    )
    
    args = parser.parse_args()
    
    agent = AutoTestAgent(
        server_url=args.server,
        agent_name=args.name,
        heartbeat_interval=args.interval
    )
    
    try:
        agent.start()
        # 保持主进程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received interrupt, stopping agent...")
        agent.stop()
    except Exception as e:
        logger.error(f"Agent error: {e}")
        agent.stop()


if __name__ == "__main__":
    main()
