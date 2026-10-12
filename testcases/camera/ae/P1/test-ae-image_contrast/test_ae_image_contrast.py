"""CAM-AE-008 图像对比度"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import exposure_distribution

CASE_LIMITS = {"contrast_min": 5, "contrast_max": 100}
METRIC_KEYS = ("rms_contrast",)


def check(metrics, limits, expected_size):
    value = metrics["rms_contrast"]
    ok = limits["contrast_min"] <= value <= limits["contrast_max"]
    return ok, f"RMS对比度={value:.2f}，要求 {limits['contrast_min']}～{limits['contrast_max']}"


@autotest(case_id="CAM-AE-008", title="CAM-AE-008 图像对比度", priority="P1", test_class="曝光 / AE",
          description="检查全图亮度RMS对比度。", expected_result="contrast_min ≤ RMS contrast ≤ contrast_max。", parameters=CASE_LIMITS)
def test_ae_image_contrast(request, record_property):
    with camera_case(request, record_property, CASE_LIMITS) as run:
        metrics = exposure_distribution(run.rgb)
        ok, reason = check(metrics, run.limits, run.expected_size)
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
