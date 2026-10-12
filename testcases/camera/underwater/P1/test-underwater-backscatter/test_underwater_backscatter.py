"""CAM-UW-005：水下散射颗粒
测试大类：水下成像 / 散射颗粒 / P1。
目的：使用局部亮点统计代理水下散射颗粒数量。
前置条件：使用真实水下图片；缺少规定的散射场景时只能记录代理结果或N/A。
判定标准：hot_pixel_count不得超过backscatter_max；该结果仅用于基础筛查。
图片来源：--picture优先，其次读取images.output，最后读取images.default；由camera_case统一准备。
阈值来源：backscatter_max来自本文件CASE_LIMITS；局部亮点统计是代理阈值，不替代颗粒标定规格。
"""

from autotest_runner import autotest

from autotest_runner.camera.advanced import evaluate

from autotest_runner.camera.execution import camera_case

CASE_LIMITS = {
    # 局部亮点数量代理的最大阈值。
    "backscatter_max": 100,
}

METRIC_KEYS = (
    # 记录局部亮点数量代理值，用于判定和证据。
    "hot_pixel_count",
    # 记录图像中位亮度，用于解释亮点检测结果。
    "median_luma",
)

def check(metrics, limits, expected_size):
    """按局部亮点代理规则返回判定结果和中文原因。

    输入为公共指标、已合并阈值和期望尺寸；输出为通过标志及中文原因。
    当前算法以hot_pixel_count作为散射颗粒的基础代理，不代表正式颗粒识别结果。
    输入不满足规定场景时由执行层记录N/A，不伪造产品质量PASS。
    """
    ok = metrics['hot_pixel_count'] <= limits['backscatter_max']
    reason = (
        f"亮点代理数={metrics['hot_pixel_count']}，"
        f"要求 ≤ {limits['backscatter_max']}"
    )
    return ok, reason

@autotest(
    case_id='CAM-UW-005',
    title='CAM-UW-005 水下散射颗粒',
    priority="P1",
    test_class='水下画质 / Underwater IQ',
    description=(
        '使用局部亮点统计作为水下散射颗粒代理算法；输入限制不满足时记录N/A，'
        '结果不代表正式颗粒识别验收。'
    ),
    expected_result=(
        '散射亮点代理数不超过阈值；缺少规定散射场景时保持N/A语义，'
        '不将代理结果解释为产品质量结论。'
    ),
    parameters=CASE_LIMITS,
)
def test_underwater_backscatter(request, record_property):
    """执行水下散射颗粒代理检查。

    五步流程为准备输入、计算指标、执行判定、记录证据和显式报告失败。
    """
    # 1. 公共准备：读取真实图片、输入限制和生效阈值。
    with camera_case(
        request,
        record_property,
        CASE_LIMITS,
    ) as run:
        # 2. 指标计算：调用已有公共代理算法。
        metrics = evaluate(
            'defect',
            run,
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
