"""CAM-COLOR-003 灰卡R/G比例"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import color_metrics

CASE_LIMITS = {"rg_min": 0.85, "rg_max": 1.15}
METRIC_KEYS = ("red_green_ratio",)


def check(metrics, limits, expected_size):
    value = metrics["red_green_ratio"]
    return limits["rg_min"] <= value <= limits["rg_max"], f"R/G={value:.3f}，要求 {limits['rg_min']}～{limits['rg_max']}"


@autotest(case_id="CAM-COLOR-003", title="CAM-COLOR-003 灰卡R/G比例", priority="P1", test_class="白平衡 / AWB & Color", description="检查中性灰场的红绿通道比例。", expected_result="rg_min ≤ R/G ≤ rg_max。", parameters=CASE_LIMITS)
def test_awb_red_green_ratio(request, record_property):
    with camera_case(request, record_property, CASE_LIMITS) as run:
        metrics = color_metrics(run.rgb)
        ok, reason = check(metrics, run.limits, run.expected_size)
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
