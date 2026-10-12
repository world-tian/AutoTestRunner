"""CAM-UW-003：水下白平衡
测试大类：水下成像 / 自动白平衡 / P1。
目的：使用RGB通道比代理检查水下白平衡偏移。
前置条件：使用真实水下图片；缺少灰卡或规定色彩输入时只能记录代理结果或N/A。
判定标准：R/G和B/G均须落在各自CASE_LIMITS范围内。
图片来源：--picture优先，其次读取images.output，最后读取images.default；由camera_case统一准备。
阈值来源：rg_min、rg_max、bg_min、bg_max来自本文件CASE_LIMITS；通道比是代理阈值。
"""

from autotest_runner import autotest

from autotest_runner.camera.metrics import color_metrics

from autotest_runner.camera.execution import camera_case

CASE_LIMITS = {
    # R/G通道比代理的最低阈值。
    "rg_min": 0.7,
    # R/G通道比代理的最高阈值。
    "rg_max": 1.3,
    # B/G通道比代理的最低阈值。
    "bg_min": 0.7,
    # B/G通道比代理的最高阈值。
    "bg_max": 1.3,
}

METRIC_KEYS = (
    # 记录R/G通道比代理值，用于判定和证据。
    "red_green_ratio",
    # 记录B/G通道比代理值，用于判定和证据。
    "blue_green_ratio",
)

def check(metrics, limits, expected_size):
    """按RGB通道比代理规则返回判定结果和中文原因。

    输入为公共指标、已合并阈值和期望尺寸；输出为通过标志及中文原因。
    check只执行本用例代理判定，不负责生成指标；缺少规定输入时保留N/A语义。
    """
    red_green_ok = limits['rg_min'] <= metrics['red_green_ratio'] <= limits['rg_max']
    blue_green_ok = limits['bg_min'] <= metrics['blue_green_ratio'] <= limits['bg_max']
    ok = red_green_ok and blue_green_ok
    reason = (
        f"R/G={metrics['red_green_ratio']:.3f}，"
        f"B/G={metrics['blue_green_ratio']:.3f}"
    )
    return ok, reason

@autotest(
    case_id='CAM-UW-003',
    title='CAM-UW-003 水下白平衡',
    priority="P1",
    test_class='水下画质 / Underwater IQ',
    description=(
        '使用RGB通道比作为水下白平衡代理算法；输入限制不满足时记录N/A，'
        '结果不代表正式白平衡验收。'
    ),
    expected_result=(
        'R/G和B/G均在对应阈值内；缺少灰卡或规定色彩输入时保持N/A语义，'
        '不将代理结果解释为产品质量结论。'
    ),
    parameters=CASE_LIMITS,
)
def test_underwater_awb(request, record_property):
    """执行水下自动白平衡代理检查。

    五步流程为准备输入、计算指标、执行判定、记录证据和显式报告失败。
    """
    # 1. 公共准备：读取真实图片、输入限制和生效阈值。
    with camera_case(
        request,
        record_property,
        CASE_LIMITS,
    ) as run:
        # 2. 指标计算：调用已有公共代理算法。
        metrics = color_metrics(
            run.rgb,
        )
        # 3. 判定：调用本脚本逻辑比较关键指标和阈值。
        ok, reason = check(
            metrics,
            run.limits,
            run.expected_size,
        )
        # 4. 记录：保存指标、判定和证据，供报告复核。
        run.record(
            metrics,
            ok,
            reason,
            METRIC_KEYS,
        )
        # 5. 失败：显式抛出异常，不吞掉判定结果。
        if not ok:
            raise AssertionError(
                f"{run.case_id}: {reason}"
            )
