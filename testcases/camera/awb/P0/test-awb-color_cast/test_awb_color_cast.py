"""CAM-COLOR-002 明显偏色检测
测试大类：白平衡 / AWB & Color
目的：初步判断 AWB 或 ISP 色彩异常
前置条件：均匀照明的中性灰卡，等待AWB稳定；不能使用任意彩色场景
判定标准：中性灰场 RGB 通道均值的（最大值−最小值）/三通道均值 ≤ 0.15，且最低通道均值 ≥ 10。
图片来源：默认读取 camera/config.json 的 images.awb，未配置时读取 images.default；
          单次运行的 --picture 优先级最高。CAMERA_CONFIG 仅用于指定另一份 config.json。
阈值来源：色偏上限 color_cast_max=0.15 在本脚本 CASE_LIMITS；通道下限 channel_min=10 在 camera/common.json。
"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import color_metrics


# 本用例独立维护判定；只有多用例复用的阈值来自 camera/common.json。
# color_cast_max：RGB 通道均值极差/总体均值上限；通道下限见 common.json。
CASE_LIMITS = {"color_cast_max":0.15}


METRIC_KEYS = ("color_cast", "rgb_mean")  # 终端与报告只展示本用例关心的实测指标。


def check(m, limits, expected_size):
    """返回本用例判定结果和包含实测值的中文原因。"""
    v = m['color_cast']
    minimum = min(m['rgb_mean'])
    ok = v <= limits['color_cast_max'] and minimum >= limits['channel_min']
    return ok, f"色偏={v:.3f}，要求 ≤ {limits['color_cast_max']}；最暗通道={minimum:.2f}，要求 ≥ {limits['channel_min']}"


@autotest(case_id="CAM-COLOR-002", title="CAM-COLOR-002 明显偏色检测", priority="P0", test_class="白平衡 / AWB & Color",
          description="明显偏色检测；判定标准：中性灰场 RGB 通道均值的（最大值−最小值）/三通道均值 ≤ 0.15，且最低通道均值 ≥ 10。",
          expected_result="中性灰场 RGB 通道均值的（最大值−最小值）/三通道均值 ≤ 0.15，且最低通道均值 ≥ 10。",
          parameters={"color_cast_max":0.15,"channel_min":10})
def test_awb_color_cast(request, record_property):
    # 1. 公共准备只负责加载真实图片与阈值；编号来自 @autotest 元数据。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 2. 明确调用本用例需要的公共指标函数，再调用上方独立判定。
        metrics = color_metrics(run.rgb)
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 3. 记录实测值和判定，失败时在本脚本显式抛出异常。
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
