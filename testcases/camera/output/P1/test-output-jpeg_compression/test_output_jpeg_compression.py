"""CAM-IMG-007：JPEG异常压缩
测试大类：输出质量 / 图像异常。
目的：使用块效应指标代理检查 JPEG 输出是否存在明显异常压缩。
前置条件：提供真实 JPEG/JPG 图片；非 JPEG 输入不满足本用例前置条件。
判定标准：输入格式为 JPEG/JPG 且 jpeg_blockiness 不超过上限。
图片来源：camera_case 按 --picture 优先，其次读取 images.output，最后使用 images.default。
阈值来源：jpeg_blockiness_max 由本文件 CASE_LIMITS 定义，属于基础代理筛查阈值。
"""

from autotest_runner import autotest

from autotest_runner.camera.advanced import evaluate

from autotest_runner.camera.execution import camera_case

CASE_LIMITS = {
    # JPEG 块效应指标的最大允许值；超过该值判定为异常压缩代理失败。
    "jpeg_blockiness_max": 35.0,
}

METRIC_KEYS = (
    # 图片格式，用于确认 JPEG/JPG 前置条件。
    "format",
    # 公共代理算法计算的 JPEG 块效应指标。
    "jpeg_blockiness",
)


def check(metrics, limits, expected_size):
    """执行 JPEG 异常压缩代理判定并返回中文原因。

    输入是指标字典、已合并阈值和期望尺寸；输出是布尔判定及原因。
    本函数只检查格式前置条件和块效应阈值，不负责生成指标。
    非 JPEG 输入属于 N/A 语义，不将其当作正式产品质量结论。
    """
    format_ok = metrics["format"] in {"JPEG", "JPG"}
    blockiness_ok = metrics["jpeg_blockiness"] <= limits["jpeg_blockiness_max"]
    if not format_ok:
        return False, f"输入不适用（N/A）：格式={metrics['format']}，需要 JPEG/JPG。"
    if not blockiness_ok:
        return False, (
            f"格式={metrics['format']}，块效应={metrics['jpeg_blockiness']:.3f}，"
            f"超过上限 {limits['jpeg_blockiness_max']}"
        )
    return True, (
        f"格式={metrics['format']}，块效应={metrics['jpeg_blockiness']:.3f}，"
        f"不超过上限 {limits['jpeg_blockiness_max']}"
    )

@autotest(
    case_id="CAM-IMG-007",
    title="CAM-IMG-007 JPEG异常压缩",
    priority="P1",
    test_class="基础图像 / Output",
    description=(
        "使用 JPEG 块效应作为异常压缩代理算法；要求输入为 JPEG/JPG。"
        "输入格式限制不满足时记录 N/A，不将结果解释为正式压缩质量验收。"
    ),
    expected_result=(
        "输入为 JPEG/JPG 且块效应不超过 jpeg_blockiness_max。"
        "该结果仅代表基础代理检查，输入限制不满足时必须记录 N/A。"
    ),
    parameters=CASE_LIMITS,
)
def test_output_jpeg_compression(request, record_property):
    """按五步流程执行 JPEG 异常压缩代理检查。"""
    # 第一步：准备真实图片、输入限制和生效阈值。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 第二步：调用公共 JPEG 压缩代理算法计算指标。
        metrics = evaluate('compression', run)
        # 第三步：调用本脚本判定逻辑比较指标和阈值。
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 第四步：保存指标、判定和证据，供报告复核。
        run.record(metrics, ok, reason, METRIC_KEYS)
        # 第五步：失败时显式抛出异常，不吞掉判定结果。
        if ok is False:
            raise AssertionError(f"{run.case_id}: {reason}")
