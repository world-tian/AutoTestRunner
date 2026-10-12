"""CAM-COLOR-005 中性误差"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import color_metrics

CASE_LIMITS = {"neutral_error_max": 12}
METRIC_KEYS = ("neutral_error",)


def check(metrics, limits, expected_size):
    value = metrics["neutral_error"]
    return value <= limits["neutral_error_max"], f"中性误差={value:.2f}，要求 ≤ {limits['neutral_error_max']}"


@autotest(case_id="CAM-COLOR-005", title="CAM-COLOR-005 中性误差", priority="P1", test_class="白平衡 / AWB & Color", description="检查中性灰场三通道离散程度。", expected_result="neutral_error ≤ neutral_error_max。", parameters=CASE_LIMITS)
def test_awb_neutral_error(request, record_property):
    with camera_case(request, record_property, CASE_LIMITS) as run:
        metrics = color_metrics(run.rgb)
        ok, reason = check(metrics, run.limits, run.expected_size)
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
