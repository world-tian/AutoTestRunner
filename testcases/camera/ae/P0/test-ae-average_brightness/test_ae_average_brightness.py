"""CAM-AE-001 平均亮度
测试大类：曝光 / AE
目的：验证整体曝光水平
前置条件：固定光源、构图的标准曝光场景，等待曝光稳定
判定标准：全图平均亮度 Y 在 60～200 之间，包含端点。
图片来源：默认读取 camera/config.json 的 images.ae，未配置时读取 images.default；
          单次运行的 --picture 优先级最高。CAMERA_CONFIG 仅用于指定另一份 config.json。
阈值来源：下限 mean_min=60 来自 camera/common.json；上限 mean_max=200 来自本脚本 CASE_LIMITS。
"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import exposure_metrics


# 本用例独立维护判定；只有多用例复用的阈值来自 camera/common.json。
# mean_max：允许的最高平均亮度；最低值 mean_min 在 camera/common.json。
CASE_LIMITS = {"mean_max":200}


METRIC_KEYS = ("mean_luma",)  # 终端与报告只展示本用例关心的实测指标。


def check(m, limits, expected_size):
    """返回本用例判定结果和包含实测值的中文原因。"""
    v = m['mean_luma']
    return limits['mean_min'] <= v <= limits['mean_max'], f"平均亮度={v:.2f}，要求 {limits['mean_min']}～{limits['mean_max']}"


@autotest(case_id="CAM-AE-001", title="CAM-AE-001 平均亮度", priority="P0", test_class="曝光 / AE",
          description="平均亮度；判定标准：全图平均亮度 Y 在 60～200 之间，包含端点。",
          expected_result="全图平均亮度 Y 在 60～200 之间，包含端点。",
          parameters={"mean_min":60,"mean_max":200})
def test_ae_average_brightness(request, record_property):
    # 1. 公共准备只负责加载真实图片与阈值；编号来自 @autotest 元数据。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 2. 明确调用本用例需要的公共指标函数，再调用上方独立判定。
        metrics = exposure_metrics(run.rgb)
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 3. 记录实测值和判定，失败时在本脚本显式抛出异常。
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
