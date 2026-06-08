from pathlib import Path

from autotest_runner.core.plan_parser import load_test_plan


def test_load_test_plan_merges_hardware_defaults(tmp_path):
    plan_file = tmp_path / "plan.yaml"
    plan_file.write_text(
        """
name: Demo
targets:
  - tests/demo.py
serial:
  enabled: true
  port: /dev/ttyUSB9
adb:
  collect_on_fail:
    screenshot: false
""",
        encoding="utf-8",
    )

    plan = load_test_plan(str(plan_file))

    assert plan["name"] == "Demo"
    assert plan["targets"] == ["tests/demo.py"]
    assert plan["execution"]["continue_on_fail"] is True
    assert plan["serial"]["enabled"] is True
    assert plan["serial"]["port"] == "/dev/ttyUSB9"
    assert plan["serial"]["fail_patterns"] == []
    assert plan["adb"]["collect_on_fail"]["screenshot"] is False
    assert plan["adb"]["collect_on_fail"]["logcat"] is True
