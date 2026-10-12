"""CAM-AE-007 有效动态范围"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import exposure_metrics, exposure_percentiles

CASE_LIMITS = {"dynamic_range_min": 20, "dynamic_range_max": 245}
METRIC_KEYS = ("effective_dynamic_range",)


def check(metrics, limits, expected_size):
    value = metrics["effective_dynamic_range"]
    ok = limits["dynamic_range_min"] <= value <= limits["dynamic_range_max"]
    return ok, f"P95-P5={value:.2f}，要求 {limits['dynamic_range_min']}～{limits['dynamic_range_max']}"


@autotest(case_id="CAM-AE-007", title="CAM-AE-007 有效动态范围", priority="P1", test_class="曝光 / AE",
          description="检查P5到P95的有效亮度范围。", expected_result="dynamic_range_min ≤ P95-P5 ≤ dynamic_range_max。", parameters=CASE_LIMITS)
def test_ae_effective_dynamic_range(request, record_property):
    with camera_case(request, record_property, CASE_LIMITS) as run:
        metrics = {**exposure_percentiles(run.rgb), **exposure_metrics(run.rgb)}
        metrics["effective_dynamic_range"] = metrics["luma_p95"] - metrics["luma_p5"]
        ok, reason = check(metrics, run.limits, run.expected_size)
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
