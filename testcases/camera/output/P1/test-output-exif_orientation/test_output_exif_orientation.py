"""CAM-IMG-004 EXIF方向
测试大类：基础图像 / Output
目的：确认图片方向元数据有效；缺失时按默认方向1处理。
"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import output_format_metrics

CASE_LIMITS = {"orientation_min": 1, "orientation_max": 8}
METRIC_KEYS = ("exif_orientation",)


def check(metrics, limits, expected_size):
    value = metrics["exif_orientation"]
    ok = limits["orientation_min"] <= value <= limits["orientation_max"]
    return ok, f"EXIF Orientation={value}，要求 {limits['orientation_min']}～{limits['orientation_max']}"


@autotest(case_id="CAM-IMG-004", title="CAM-IMG-004 EXIF方向", priority="P1", test_class="基础图像 / Output",
          description="检查原始图片 EXIF Orientation 是否有效，缺失时按默认方向1处理。",
          expected_result="EXIF Orientation 为 1～8。", parameters=CASE_LIMITS)
def test_output_exif_orientation(request, record_property):
    with camera_case(request, record_property, CASE_LIMITS) as run:
        metrics = output_format_metrics(run.image_path)
        ok, reason = check(metrics, run.limits, run.expected_size)
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
