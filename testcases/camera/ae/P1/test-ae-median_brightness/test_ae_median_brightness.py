"""CAM-AE-006 亮度中位数
测试大类：曝光 / AE
目的：减少少量极端像素对整体曝光判断的影响。
"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import exposure_median

CASE_LIMITS = {"median_min": 60, "median_max": 200}
METRIC_KEYS = ("median_luma",)


def check(metrics, limits, expected_size):
    value = metrics["median_luma"]
    ok = limits["median_min"] <= value <= limits["median_max"]
    return ok, f"亮度中位数={value:.2f}，要求 {limits['median_min']}～{limits['median_max']}"


@autotest(case_id="CAM-AE-006", title="CAM-AE-006 亮度中位数", priority="P1", test_class="曝光 / AE",
          description="检查亮度中位数，减少少量极端像素对整体曝光判断的影响。",
          expected_result="median_min ≤ 亮度中位数 ≤ median_max。", parameters=CASE_LIMITS)
def test_ae_median_brightness(request, record_property):
    with camera_case(request, record_property, CASE_LIMITS) as run:
        metrics = exposure_median(run.rgb)
        ok, reason = check(metrics, run.limits, run.expected_size)
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
