import json
import logging
import os
from pathlib import Path

import pytest

from autotest_runner.runtime import RuntimeManager

logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    group = parser.getgroup("autotest-runner")
    group.addoption(
        "--autotest-plan-config",
        action="store",
        default=None,
        help="AutoTestRunner runtime plan JSON file.",
    )


def pytest_configure(config):
    plan_path = config.getoption("--autotest-plan-config") or os.getenv("AUTOTEST_PLAN_CONFIG")
    if not plan_path:
        config.autotest_runtime = None
        return

    with open(plan_path, "r", encoding="utf-8") as plan_file:
        plan = json.load(plan_file)

    runtime = RuntimeManager(plan, base_dir=os.getcwd())
    runtime.start_session()
    config.autotest_runtime = runtime


def pytest_sessionfinish(session, exitstatus):
    runtime = getattr(session.config, "autotest_runtime", None)
    if runtime:
        runtime.finish_session()


@pytest.fixture
def serial(request):
    runtime = getattr(request.config, "autotest_runtime", None)
    if not runtime or not runtime.serial_tool:
        pytest.skip("Serial is not enabled in AutoTestRunner plan")
    return runtime.serial_tool


@pytest.fixture
def adb(request):
    runtime = getattr(request.config, "autotest_runtime", None)
    if not runtime or not runtime.adb_tool:
        pytest.skip("ADB is not enabled in AutoTestRunner plan")
    return runtime.adb_tool


def pytest_runtest_setup(item):
    runtime = getattr(item.config, "autotest_runtime", None)
    if runtime:
        item.autotest_case_state = runtime.before_case(item.nodeid)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call":
        return

    runtime = getattr(item.config, "autotest_runtime", None)
    if not runtime:
        return

    status = "passed" if report.passed else "failed" if report.failed else "skipped"
    error_message = None
    if report.failed:
        error_message = str(report.longrepr)

    record = runtime.after_case(
        getattr(item, "autotest_case_state", {}),
        status,
        error_message=error_message,
    )

    if status == "passed" and record["status"] == "failed":
        report.outcome = "failed"
        report.longrepr = record["error_message"]

    if record["status"] in ("failed", "error"):
        execution_config = runtime.plan.get("execution", {})
        if execution_config.get("keep_on_fail", False):
            runtime.keep_failure_site()
            pytest.exit("Failure site kept; stopping execution as requested.", returncode=1)
        if not execution_config.get("continue_on_fail", True):
            pytest.exit("Test failed; stopping execution because continue_on_fail=false.", returncode=1)
