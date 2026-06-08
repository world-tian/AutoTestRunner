import json
import logging
import os
import time
import zipfile
from datetime import datetime
from pathlib import Path

from autotest_runner.tools.adb import ADBTool
from autotest_runner.tools.relay import RelayTool
from autotest_runner.tools.serial_port import SerialTool

logger = logging.getLogger(__name__)


def safe_name(value):
    return "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in value)


class RuntimeManager:
    """硬件测试执行生命周期管理器。"""

    def __init__(self, plan, base_dir=None):
        self.plan = plan or {}
        self.base_dir = Path(base_dir or os.getcwd())
        artifacts_config = self.plan.get("artifacts", {})
        output_dir = artifacts_config.get("output_dir", "reports/artifacts")
        run_name = datetime.now().strftime("run_%Y%m%d_%H%M%S")
        self.artifacts_dir = (self.base_dir / output_dir / run_name).resolve()
        self.case_dir = None
        self.serial_tool = None
        self.adb_tool = None
        self.case_records = []
        self.current_case = None

    def start_session(self):
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._write_json("plan_snapshot.json", self.plan)

        serial_config = self.plan.get("serial", {})
        if serial_config.get("enabled"):
            self.serial_tool = SerialTool(
                port=serial_config.get("port", "/dev/ttyUSB0"),
                baudrate=int(serial_config.get("baudrate", 115200)),
                timeout=float(serial_config.get("timeout_sec", 10)),
            )
            if serial_config.get("log", True):
                self.serial_tool.start_capture(self.artifacts_dir / "serial_session.log")

        adb_config = self.plan.get("adb", {})
        if adb_config.get("enabled"):
            self.adb_tool = ADBTool(device_id=adb_config.get("device_id") or None)

        logger.info("AutoTest runtime artifacts: %s", self.artifacts_dir)

    def finish_session(self):
        if self.serial_tool:
            self.serial_tool.stop_capture()
        self._write_json("case_results.json", {"cases": self.case_records})
        if self.plan.get("artifacts", {}).get("zip_logs", True):
            self.zip_artifacts()

    def before_case(self, nodeid):
        self.current_case = nodeid
        self.case_dir = self.artifacts_dir / "cases" / safe_name(nodeid)
        self.case_dir.mkdir(parents=True, exist_ok=True)

        serial_offset = self.serial_tool.mark() if self.serial_tool else 0
        if self.adb_tool and self.plan.get("adb", {}).get("clear_logcat_before_case", True):
            self.adb_tool.run_cmd(["logcat", "-c"], check=False, timeout=10)

        return {
            "nodeid": nodeid,
            "serial_offset": serial_offset,
            "started_at": datetime.utcnow().isoformat(),
        }

    def after_case(self, case_state, status, error_message=None):
        nodeid = case_state.get("nodeid", self.current_case)
        failed_by_serial = False
        serial_patterns = []

        if self.serial_tool:
            serial_log = self.serial_tool.get_log_since(case_state.get("serial_offset", 0))
            serial_path = self.case_dir / "serial.log"
            serial_path.write_text(serial_log, encoding="utf-8")
            fail_patterns = self.plan.get("serial", {}).get("fail_patterns", [])
            serial_patterns = self.serial_tool.find_patterns_since(
                case_state.get("serial_offset", 0),
                fail_patterns,
            )
            failed_by_serial = bool(serial_patterns)

        final_status = status
        final_error = error_message
        if status == "passed" and failed_by_serial:
            final_status = "failed"
            final_error = "Serial fail pattern matched: " + ", ".join(serial_patterns)

        if final_status in ("failed", "error"):
            self.collect_failure_artifacts(nodeid)

        should_keep = final_status in ("failed", "error") and self.plan.get("execution", {}).get("keep_on_fail", False)
        if not should_keep and self.plan.get("execution", {}).get("cleanup_between_cases", True):
            self.cleanup_case()

        record = {
            "nodeid": nodeid,
            "status": final_status,
            "error_message": final_error,
            "serial_fail_patterns": serial_patterns,
            "artifacts_dir": str(self.case_dir),
            "started_at": case_state.get("started_at"),
            "ended_at": datetime.utcnow().isoformat(),
        }
        self.case_records.append(record)
        self._write_json(self.case_dir / "result.json", record)
        return record

    def collect_failure_artifacts(self, nodeid):
        adb_config = self.plan.get("adb", {})
        collect = adb_config.get("collect_on_fail", {})
        if self.adb_tool:
            if collect.get("logcat", True):
                self._safe_collect("adb_logcat", self.adb_tool.dump_logcat, self.case_dir / "adb_logcat.log")
            if collect.get("screenshot", True):
                self._safe_collect("adb_screenshot", self.adb_tool.screenshot, self.case_dir / "screenshot.png")
            if collect.get("bugreport", False):
                self._safe_collect("adb_bugreport", self.adb_tool.bugreport, self.case_dir / "bugreport.zip")
            for remote_path in collect.get("pull_paths", []) or []:
                target = self.case_dir / "pulled" / safe_name(remote_path.strip("/").replace("/", "_"))
                self._safe_collect(f"adb_pull:{remote_path}", self.adb_tool.pull, remote_path, target)

        logger.info("Failure artifacts collected for %s", nodeid)

    def cleanup_case(self):
        cleanup = self.plan.get("cleanup", {})
        if not cleanup.get("enabled", False):
            return
        for action in cleanup.get("actions", []) or []:
            action_type = action.get("type")
            try:
                if action_type == "adb" and self.adb_tool:
                    self.adb_tool.run_cmd(action.get("command", []), check=False)
                elif action_type == "relay":
                    relay = RelayTool(action.get("ip_address") or os.getenv("DEVICE_IP", "127.0.0.1"))
                    if action.get("action") == "power_cycle":
                        relay.restart(
                            port=int(action.get("port", 1)),
                            delay_sec=int(action.get("delay_sec", 3)),
                        )
                    elif action.get("action") == "power_off":
                        relay.power_off(port=int(action.get("port", 1)))
                    elif action.get("action") == "power_on":
                        relay.power_on(port=int(action.get("port", 1)))
            except Exception as exc:
                logger.warning("Cleanup action failed: %s", exc)

    def keep_failure_site(self):
        timeout = int(self.plan.get("execution", {}).get("keep_on_fail_timeout_sec", 0) or 0)
        logger.warning("Failure site is kept. Cleanup is skipped.")
        if timeout <= 0:
            logger.warning("Waiting forever. Press Ctrl+C to release the site.")
            while True:
                time.sleep(60)
        logger.warning("Waiting %s seconds before ending the run.", timeout)
        time.sleep(timeout)

    def zip_artifacts(self):
        zip_path = self.artifacts_dir.with_suffix(".zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in self.artifacts_dir.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(self.artifacts_dir))
        logger.info("Artifacts zipped: %s", zip_path)
        return zip_path

    def _write_json(self, path, data):
        target = Path(path)
        if not target.is_absolute():
            target = self.artifacts_dir / target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _safe_collect(self, name, func, *args):
        try:
            return func(*args)
        except Exception as exc:
            message = f"{name}: {exc}\n"
            logger.warning("Artifact collection failed: %s", message.strip())
            error_log = self.case_dir / "artifact_errors.log"
            with error_log.open("a", encoding="utf-8") as log:
                log.write(message)
            return None
