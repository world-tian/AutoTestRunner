"""CAM-AE-002 欠曝比例
测试大类：曝光 / AE
目的：判断暗部是否存在明显欠曝
前置条件：固定光源、构图的标准曝光场景，等待曝光稳定
判定标准：亮度 Y≤10 的像素占全图比例 ≤ 0.15（15%）。
图片来源：默认读取 camera/config.json 的 images.ae，未配置时读取 images.default；
          单次运行的 --picture 优先级最高。CAMERA_CONFIG 仅用于指定另一份 config.json。
阈值来源：Y≤10 是公共曝光指标中的暗像素定义；比例上限 under_max=0.15 在本脚本 CASE_LIMITS。
"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import exposure_metrics


# 本用例独立维护判定；只有多用例复用的阈值来自 camera/common.json。
# under_max：亮度 Y≤10 的像素占比上限。
CASE_LIMITS = {"under_max":0.15}


METRIC_KEYS = ("under_ratio",)  # 终端与报告只展示本用例关心的实测指标。


def check(m, limits, expected_size):
    """返回本用例判定结果和包含实测值的中文原因。"""
    v = m['under_ratio']
    return v <= limits['under_max'], f"欠曝像素比例={v:.3f}，要求 ≤ {limits['under_max']}"


@autotest(case_id="CAM-AE-002", title="CAM-AE-002 欠曝比例", priority="P0", test_class="曝光 / AE",
          description="欠曝比例；判定标准：亮度 Y≤10 的像素占全图比例 ≤ 0.15（15%）。",
          expected_result="亮度 Y≤10 的像素占全图比例 ≤ 0.15（15%）。",
          parameters={"dark_pixel_y_max":10,"under_max":0.15})
def test_ae_underexposure_ratio(request, record_property):
    # 1. 公共准备只负责加载真实图片与阈值；编号来自 @autotest 元数据。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 2. 明确调用本用例需要的公共指标函数，再调用上方独立判定。
        metrics = exposure_metrics(run.rgb)
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 3. 记录实测值和判定，失败时在本脚本显式抛出异常。
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
