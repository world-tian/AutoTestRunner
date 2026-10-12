"""CAM-COLOR-004 灰卡B/G比例"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import color_metrics

CASE_LIMITS = {"bg_min": 0.85, "bg_max": 1.15}
METRIC_KEYS = ("blue_green_ratio",)


def check(metrics, limits, expected_size):
    value = metrics["blue_green_ratio"]
    return limits["bg_min"] <= value <= limits["bg_max"], f"B/G={value:.3f}，要求 {limits['bg_min']}～{limits['bg_max']}"


@autotest(case_id="CAM-COLOR-004", title="CAM-COLOR-004 灰卡B/G比例", priority="P1", test_class="白平衡 / AWB & Color", description="检查中性灰场的蓝绿通道比例。", expected_result="bg_min ≤ B/G ≤ bg_max。", parameters=CASE_LIMITS)
def test_awb_blue_green_ratio(request, record_property):
    with camera_case(request, record_property, CASE_LIMITS) as run:
        metrics = color_metrics(run.rgb)
        ok, reason = check(metrics, run.limits, run.expected_size)
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
