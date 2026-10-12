"""CAM-SHP-006 梯度清晰度"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import tenengrad

CASE_LIMITS = {"tenengrad_min": 100}
METRIC_KEYS = ("tenengrad",)


def check(metrics, limits, expected_size):
    value = metrics["tenengrad"]
    ok = value >= limits["tenengrad_min"]
    return ok, f"Tenengrad={value:.2f}，要求 ≥ {limits['tenengrad_min']}"


@autotest(case_id="CAM-SHP-006", title="CAM-SHP-006 梯度清晰度", priority="P1", test_class="清晰度 / Sharpness",
          description="使用Sobel梯度能量补充Laplacian清晰度。", expected_result="Tenengrad ≥ tenengrad_min。", parameters=CASE_LIMITS)
def test_sharpness_tenengrad(request, record_property):
    with camera_case(request, record_property, CASE_LIMITS) as run:
        metrics = tenengrad(run.rgb)
        ok, reason = check(metrics, run.limits, run.expected_size)
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
