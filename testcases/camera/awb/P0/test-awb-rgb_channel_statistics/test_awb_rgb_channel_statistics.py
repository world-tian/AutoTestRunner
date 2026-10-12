"""CAM-COLOR-001 RGB 通道统计
测试大类：白平衡 / AWB & Color
目的：验证 RGB 通道及颜色输出基础状态
前置条件：均匀照明的中性灰卡，等待AWB稳定；不能使用任意彩色场景
判定标准：R、G、B 三通道全图均值分别位于 10～245，包含端点；通道标准差只记录，不参与判定。
图片来源：默认读取 camera/config.json 的 images.awb，未配置时读取 images.default；
          单次运行的 --picture 优先级最高。CAMERA_CONFIG 仅用于指定另一份 config.json。
阈值来源：通道下限 channel_min=10 来自 camera/common.json；上限 channel_max=245 在本脚本 CASE_LIMITS。
"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import color_metrics


# 本用例独立维护判定；只有多用例复用的阈值来自 camera/common.json。
# channel_max：RGB 各通道均值上限；下限 channel_min 在 common.json。
CASE_LIMITS = {"channel_max":245}


METRIC_KEYS = ("rgb_mean", "rgb_std")  # 终端与报告只展示本用例关心的实测指标。


def check(m, limits, expected_size):
    """返回本用例判定结果和包含实测值的中文原因。"""
    values = m['rgb_mean']
    ok = all(limits['channel_min'] <= v <= limits['channel_max'] for v in values)
    return ok, f"RGB均值={values}，各通道要求 {limits['channel_min']}～{limits['channel_max']}"


@autotest(case_id="CAM-COLOR-001", title="CAM-COLOR-001 RGB 通道统计", priority="P0", test_class="白平衡 / AWB & Color",
          description="RGB 通道统计；判定标准：R、G、B 三通道全图均值分别位于 10～245，包含端点；通道标准差只记录，不参与判定。",
          expected_result="R、G、B 三通道全图均值分别位于 10～245，包含端点；通道标准差只记录，不参与判定。",
          parameters={"channel_min":10,"channel_max":245})
def test_awb_rgb_channel_statistics(request, record_property):
    # 1. 公共准备只负责加载真实图片与阈值；编号来自 @autotest 元数据。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 2. 明确调用本用例需要的公共指标函数，再调用上方独立判定。
        metrics = color_metrics(run.rgb)
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 3. 记录实测值和判定，失败时在本脚本显式抛出异常。
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
