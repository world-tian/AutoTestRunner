"""CAM-COLOR-006：ColorChecker色差基础代理
测试大类：自动白平衡 / 色彩。
目的：用中性色误差代理检查 ColorChecker 场景的色彩偏移。
前置条件：使用真实综合色卡或灰卡图片；正式 DeltaE2000 验收需要已定位的标准色卡。
判定标准：neutral_error 代理指标不超过 delta_e_max。
图片来源：camera_case 按 --picture 优先，其次读取 images.output，最后使用 images.default。
阈值来源：delta_e_max 由本文件 CASE_LIMITS 定义，当前仅作基础代理筛查阈值。
"""

from autotest_runner import autotest

from autotest_runner.camera.metrics import color_metrics

from autotest_runner.camera.execution import camera_case

CASE_LIMITS = {
    # 中性色误差代理的最大允许值，正式 DeltaE2000 阈值需由标定数据确认。
    "delta_e_max": 12.0,
}

METRIC_KEYS = (
    # 中性色误差代理，用于和 delta_e_max 比较。
    "neutral_error",
    # 公共色彩指标计算的色偏结果，用于报告复核。
    "color_cast",
)


def check(metrics, limits, expected_size):
    """执行 ColorChecker 色差基础代理判定并返回中文原因。

    输入是指标字典、已合并阈值和期望尺寸；输出是布尔判定及原因。
    本函数只比较公共色彩指标与 CASE_LIMITS，不负责生成指标。
    未定位标准色卡时，结果仅代表中性色差代理检查并保留 N/A 语义。
    """
    value = metrics["neutral_error"]
    ok = value <= limits["delta_e_max"]
    if ok:
        reason = f"中性色差代理={value:.3f}，不超过上限 {limits['delta_e_max']}"
    else:
        reason = f"中性色差代理={value:.3f}，超过上限 {limits['delta_e_max']}"
    return ok, reason

@autotest(
    case_id="CAM-COLOR-006",
    title="CAM-COLOR-006 ColorChecker色差基础代理",
    priority="P1",
    test_class="白平衡 / AWB & Color",
    description=(
        "使用中性色误差作为 ColorChecker 色差代理算法；正式 DeltaE2000 验收要求标准色卡定位。"
        "输入限制不满足时记录 N/A，不将基础代理结果解释为正式色差结论。"
    ),
    expected_result=(
        "neutral_error 代理值不超过 delta_e_max。"
        "缺少标准色卡或定位信息时仅记录代理检查结果，并保留 N/A 语义。"
    ),
    parameters=CASE_LIMITS,
)
def test_awb_colorchecker_delta_e(request, record_property):
    """按五步流程执行 ColorChecker 色差基础代理检查。"""
    # 第一步：准备真实图片、输入限制和生效阈值。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 第二步：调用公共色彩指标函数计算代理指标。
        metrics = color_metrics(run.rgb)
        # 第三步：调用本脚本判定逻辑比较指标和阈值。
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 第四步：保存指标、判定和证据，供报告复核。
        run.record(metrics, ok, reason, METRIC_KEYS)
        # 第五步：失败时显式抛出异常，不吞掉判定结果。
        if ok is False:
            raise AssertionError(f"{run.case_id}: {reason}")
