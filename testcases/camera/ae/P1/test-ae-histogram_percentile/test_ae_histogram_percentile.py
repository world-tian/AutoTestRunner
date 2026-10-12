"""CAM-AE-005 亮度直方图分位数
测试大类：曝光 / AE
目的：识别平均亮度正常但暗部或高光分布异常的图像
前置条件：固定光源、构图的标准曝光场景，等待曝光稳定
判定标准：P1、P5、P50、P95、P99 均处于当前场景阈值范围。
"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import exposure_percentiles


CASE_LIMITS = {
    "p1_min": 5,
    "p5_min": 15,
    "p50_min": 60,
    "p95_max": 240,
    "p99_max": 250,
}

METRIC_KEYS = ("luma_p1", "luma_p5", "luma_p50", "luma_p95", "luma_p99")


def check(metrics, limits, expected_size):
    checks = (
        metrics["luma_p1"] >= limits["p1_min"],
        metrics["luma_p5"] >= limits["p5_min"],
        metrics["luma_p50"] >= limits["p50_min"],
        metrics["luma_p95"] <= limits["p95_max"],
        metrics["luma_p99"] <= limits["p99_max"],
    )
    reason = (
        f"P1/P5/P50/P95/P99="
        f"{metrics['luma_p1']:.2f}/{metrics['luma_p5']:.2f}/"
        f"{metrics['luma_p50']:.2f}/{metrics['luma_p95']:.2f}/"
        f"{metrics['luma_p99']:.2f}，要求 P1≥{limits['p1_min']}、"
        f"P5≥{limits['p5_min']}、P50≥{limits['p50_min']}、"
        f"P95≤{limits['p95_max']}、P99≤{limits['p99_max']}"
    )
    return all(checks), reason


@autotest(case_id="CAM-AE-005", title="CAM-AE-005 亮度直方图分位数", priority="P1", test_class="曝光 / AE",
          description="检查 P1/P5/P50/P95/P99 亮度分位数，避免均值掩盖暗部或高光异常。",
          expected_result="P1≥5、P5≥15、P50≥60、P95≤240、P99≤250。",
          parameters=CASE_LIMITS)
def test_ae_histogram_percentile(request, record_property):
    with camera_case(request, record_property, CASE_LIMITS) as run:
        metrics = exposure_percentiles(run.rgb)
        ok, reason = check(metrics, run.limits, run.expected_size)
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")