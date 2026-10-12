"""CAM-SHP-004 中心/四角清晰度一致性
测试大类：清晰度 / Sharpness
目的：辅助发现镜头倾斜、AA、组装问题
前置条件：固定光源、距离、分辨率；中心和四角包含相同重复纹理图卡
判定标准：中心与四角五区清晰度最小/最大比 ≥ 0.4，且每区 Laplacian 方差 ≥ 80。
图片来源：默认读取 camera/config.json 的 images.sharpness，未配置时读取 images.default；
          单次运行的 --picture 优先级最高。CAMERA_CONFIG 仅用于指定另一份 config.json。
阈值来源：比值下限 sharpness_ratio_min=0.4 在本脚本 CASE_LIMITS；各区下限 sharpness_min=80 在 camera/common.json。
"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import sharpness_metrics


# 本用例独立维护判定；只有多用例复用的阈值来自 camera/common.json。
# sharpness_ratio_min：中心和四角五区的最小/最大清晰度比；各区下限见 common.json。
CASE_LIMITS = {"sharpness_ratio_min":0.4}


METRIC_KEYS = ("sharpness_ratio", "roi_sharpness")  # 终端与报告只展示本用例关心的实测指标。


def check(m, limits, expected_size):
    """返回本用例判定结果和包含实测值的中文原因。"""
    ratio = m['sharpness_ratio']
    minimum = min(m['roi_sharpness'].values())
    ok = ratio >= limits['sharpness_ratio_min'] and minimum >= limits['sharpness_min']
    return ok, f"五区最小/最大比={ratio:.3f}，要求 ≥ {limits['sharpness_ratio_min']}；最小清晰度={minimum:.2f}，要求 ≥ {limits['sharpness_min']}"


@autotest(case_id="CAM-SHP-004", title="CAM-SHP-004 中心/四角清晰度一致性", priority="P0", test_class="清晰度 / Sharpness",
          description="中心/四角清晰度一致性；判定标准：中心与四角五区清晰度最小/最大比 ≥ 0.4，且每区 Laplacian 方差 ≥ 80。",
          expected_result="中心与四角五区清晰度最小/最大比 ≥ 0.4，且每区 Laplacian 方差 ≥ 80。",
          parameters={"sharpness_ratio_min":0.4,"sharpness_min":80})
def test_sharpness_center_corner_consistency(request, record_property):
    # 1. 公共准备只负责加载真实图片与阈值；编号来自 @autotest 元数据。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 2. 明确调用本用例需要的公共指标函数，再调用上方独立判定。
        metrics = sharpness_metrics(run.rgb)
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 3. 记录实测值和判定，失败时在本脚本显式抛出异常。
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
