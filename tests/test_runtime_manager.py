import json
import zipfile

from autotest_runner.runtime import RuntimeManager


def test_runtime_manager_writes_case_result_and_zip(tmp_path):
    plan = {
        "artifacts": {"output_dir": "artifacts", "zip_logs": True},
        "execution": {"cleanup_between_cases": True, "keep_on_fail": False},
        "cleanup": {"enabled": False, "actions": []},
        "serial": {"enabled": False},
        "adb": {"enabled": False},
    }
    runtime = RuntimeManager(plan, base_dir=tmp_path)

    runtime.start_session()
    case_state = runtime.before_case("tests/test_demo.py::test_ok")
    record = runtime.after_case(case_state, "passed")
    runtime.finish_session()

    result_file = runtime.artifacts_dir / "cases" / "tests_test_demo.py__test_ok" / "result.json"
    zip_file = runtime.artifacts_dir.with_suffix(".zip")

    assert record["status"] == "passed"
    assert result_file.exists()
    assert zip_file.exists()
    assert json.loads(result_file.read_text(encoding="utf-8"))["nodeid"] == "tests/test_demo.py::test_ok"
    with zipfile.ZipFile(zip_file) as archive:
        assert "case_results.json" in archive.namelist()
