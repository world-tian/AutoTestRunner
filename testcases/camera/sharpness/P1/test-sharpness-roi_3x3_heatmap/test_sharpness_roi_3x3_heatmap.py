"""CAM-SHP-005 3×3清晰度热力图
测试大类：清晰度 / Sharpness
目的：发现画面局部清晰度下降和空间一致性异常
前置条件：固定光源、距离、分辨率；3×3区域包含可比较的纹理图卡。
判定标准：9个 ROI 清晰度均达到下限，且最小/最大比达到一致性下限。
"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import sharpness_heatmap_3x3


CASE_LIMITS = {"sharpness_ratio_min": 0.4}
METRIC_KEYS = ("sharpness_min", "sharpness_max", "sharpness_ratio", "sharpness_heatmap_3x3")


def check(metrics, limits, expected_size):
    ok = metrics["sharpness_min"] >= limits["sharpness_min"] and metrics["sharpness_ratio"] >= limits["sharpness_ratio_min"]
    reason = (
        f"3×3清晰度最小/最大比={metrics['sharpness_ratio']:.3f}，要求 ≥ {limits['sharpness_ratio_min']}；"
        f"最小清晰度={metrics['sharpness_min']:.2f}，要求 ≥ {limits['sharpness_min']}"
    )
    return ok, reason


@autotest(case_id="CAM-SHP-005", title="CAM-SHP-005 3×3清晰度热力图", priority="P1", test_class="清晰度 / Sharpness",
          description="计算3×3 ROI清晰度热力图，检查局部清晰度下限和空间一致性。",
          expected_result="9个ROI清晰度均 ≥ sharpness_min，且最小/最大 ≥ 0.4。",
          parameters={"grid_rows": 3, "grid_cols": 3, "sharpness_ratio_min": 0.4})
def test_sharpness_roi_3x3_heatmap(request, record_property):
    with camera_case(request, record_property, CASE_LIMITS) as run:
        metrics = sharpness_heatmap_3x3(run.rgb)
        ok, reason = check(metrics, run.limits, run.expected_size)
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")