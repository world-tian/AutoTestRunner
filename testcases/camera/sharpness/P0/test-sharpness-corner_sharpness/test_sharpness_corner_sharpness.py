"""CAM-SHP-003 四角区域清晰度
测试大类：清晰度 / Sharpness
目的：判断边缘成像和局部异常
前置条件：固定光源、距离、分辨率；中心和四角包含相同重复纹理图卡
判定标准：左上、右上、左下、右下四个 25% 宽×25% 高 ROI 的 Laplacian 方差分别 ≥ 80。
图片来源：默认读取 camera/config.json 的 images.sharpness，未配置时读取 images.default；
          单次运行的 --picture 优先级最高。CAMERA_CONFIG 仅用于指定另一份 config.json。
阈值来源：共享下限 sharpness_min=80 来自 camera/common.json；四角分别判断，不使用四角平均值。
"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import sharpness_metrics


# 本用例独立维护判定；只有多用例复用的阈值来自 camera/common.json。
# 四角各 ROI 的清晰度下限 sharpness_min 在 camera/common.json。
CASE_LIMITS = {}


METRIC_KEYS = ("roi_sharpness",)  # 终端与报告只展示本用例关心的实测指标。


def check(m, limits, expected_size):
    """返回本用例判定结果和包含实测值的中文原因。"""
    corners = {k: v for k, v in m['roi_sharpness'].items() if k != 'center'}
    minimum = min(corners.values())
    return minimum >= limits['sharpness_min'], f"四角最小清晰度={minimum:.2f}，要求 ≥ {limits['sharpness_min']}；各角={corners}"


@autotest(case_id="CAM-SHP-003", title="CAM-SHP-003 四角区域清晰度", priority="P0", test_class="清晰度 / Sharpness",
          description="四角区域清晰度；判定标准：左上、右上、左下、右下四个 25% 宽×25% 高 ROI 的 Laplacian 方差分别 ≥ 80。",
          expected_result="左上、右上、左下、右下四个 25% 宽×25% 高 ROI 的 Laplacian 方差分别 ≥ 80。",
          parameters={"roi_fraction":0.25,"sharpness_min":80})
def test_sharpness_corner_sharpness(request, record_property):
    # 1. 公共准备只负责加载真实图片与阈值；编号来自 @autotest 元数据。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 2. 明确调用本用例需要的公共指标函数，再调用上方独立判定。
        metrics = sharpness_metrics(run.rgb)
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 3. 记录实测值和判定，失败时在本脚本显式抛出异常。
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
