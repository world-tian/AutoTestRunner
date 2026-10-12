"""CAM-AE-009 直方图熵"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import exposure_distribution

CASE_LIMITS = {"entropy_min": 1, "entropy_max": 8}
METRIC_KEYS = ("histogram_entropy",)


def check(metrics, limits, expected_size):
    value = metrics["histogram_entropy"]
    ok = limits["entropy_min"] <= value <= limits["entropy_max"]
    return ok, f"亮度直方图熵={value:.2f}，要求 {limits['entropy_min']}～{limits['entropy_max']}"


@autotest(case_id="CAM-AE-009", title="CAM-AE-009 直方图熵", priority="P1", test_class="曝光 / AE",
          description="检查亮度直方图熵，识别分布塌缩。", expected_result="entropy_min ≤ 亮度直方图熵 ≤ entropy_max。", parameters=CASE_LIMITS)
def test_ae_histogram_entropy(request, record_property):
    with camera_case(request, record_property, CASE_LIMITS) as run:
        metrics = exposure_distribution(run.rgb)
        ok, reason = check(metrics, run.limits, run.expected_size)
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
