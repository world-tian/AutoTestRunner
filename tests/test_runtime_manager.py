import json
import zipfile

from autotest_runner.runtime import RuntimeManager
from autotest_runner.core.runner import _cleanup_camera_bytecode


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


def test_runtime_manager_copies_camera_evidence_and_images_into_zip(tmp_path):
    plan = {
        "artifacts": {"output_dir": "artifacts", "zip_logs": True, "include_camera_evidence": True},
        "execution": {"cleanup_between_cases": True, "keep_on_fail": False},
        "cleanup": {"enabled": False, "actions": []},
        "serial": {"enabled": False},
        "adb": {"enabled": False},
    }
    source_dir = tmp_path / "reports" / "camera"
    source_dir.mkdir(parents=True)
    mtf_plot = source_dir / "sample_mtf.png"
    roi_crop = source_dir / "sample_roi.png"
    mtf_plot.write_bytes(b"mtf")
    roi_crop.write_bytes(b"roi")
    evidence = source_dir / "sample.json"
    evidence.write_text(json.dumps({
        "metrics": {
            "mtf_plot": str(mtf_plot),
            "roi_crops": [str(roi_crop)],
        }
    }), encoding="utf-8")

    runtime = RuntimeManager(plan, base_dir=tmp_path)
    runtime.start_session()
    case_state = runtime.before_case("tests/test_demo.py::test_mtf")
    record = runtime.after_case(case_state, "failed", camera_evidence=str(evidence))
    runtime.finish_session()

    case_dir = runtime.artifacts_dir / "cases" / "tests_test_demo.py__test_mtf"
    zip_file = runtime.artifacts_dir.with_suffix(".zip")
    camera_files = sorted((case_dir / "camera" / "images").glob("*.png"))

    assert record["camera_evidence"]["evidence_file"].endswith("/camera/sample.json")
    assert len(record["camera_evidence"]["files"]) == 2
    assert len(camera_files) == 2
    with zipfile.ZipFile(zip_file) as archive:
        names = set(archive.namelist())
        assert "cases/tests_test_demo.py__test_mtf/camera/sample.json" in names
        assert len([name for name in names if "/camera/images/" in name and name.endswith(".png")]) == 2


def test_cleanup_camera_bytecode_removes_only_camera_caches(tmp_path):
    camera_cache = tmp_path / "testcases" / "camera" / "ae" / "__pycache__"
    other_cache = tmp_path / "testcases" / "network" / "__pycache__"
    camera_cache.mkdir(parents=True)
    other_cache.mkdir(parents=True)
    (camera_cache / "case.cpython-311.pyc").write_bytes(b"cache")
    (other_cache / "other.cpython-311.pyc").write_bytes(b"cache")

    _cleanup_camera_bytecode(tmp_path)

    assert not camera_cache.exists()
    assert other_cache.exists()
