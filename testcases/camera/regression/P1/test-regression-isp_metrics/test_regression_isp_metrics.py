"""CAM-REG-002：ISP版本指标对比
测试大类：版本回归 / ISP指标 / P1。
目的：比较新旧ISP版本的图像指标变化，当前输出基础回归代理指标。
前置条件：使用真实图片，并提供同场景旧ISP基线；缺少基线配对时记录N/A。
判定标准：基线可用时指标变化应满足regression_delta_max；当前输入不是基线对。
图片来源：--picture优先，其次读取images.output，最后读取images.default；由camera_case统一准备。
阈值来源：regression_delta_max来自本文件CASE_LIMITS；代理阈值不替代版本回归基线规格。
"""

from autotest_runner import autotest

from autotest_runner.camera.advanced import evaluate

from autotest_runner.camera.execution import camera_case

CASE_LIMITS = {
    # 新旧ISP指标变化代理值的最大阈值。
    "regression_delta_max": 0.2,
}

METRIC_KEYS = (
    # 记录ISP基线配对输入是否可用，供N/A语义和报告复核。
    "available",
    # 记录新旧ISP指标变化代理值。
    "baseline_delta",
)

def check(metrics, limits, expected_size):
    """按ISP版本指标回归代理规则返回判定结果和中文原因。

    当前输入缺少旧ISP基线配对，因此保留N/A语义并返回未通过。
    该结果不是版本质量失败，也不伪造代理算法的PASS。
    """
    ok = False
    reason = "需要配置ISP版本基线文件；当前输入不是基线对，结果为N/A"
    return ok, reason

@autotest(
    case_id='CAM-REG-002',
    title='CAM-REG-002 ISP版本指标对比',
    priority="P1",
    test_class='版本回归 / Regression',
    description=(
        '使用ISP指标变化代理算法比较固定输入与旧版本基线；缺少基线时明确记录N/A，'
        '不代表正式版本回归验收。'
    ),
    expected_result=(
        '提供规定的旧ISP基线配对输入后，指标变化代理值应满足阈值；'
        '缺少配对输入时保持N/A语义。'
    ),
    parameters=CASE_LIMITS,
)
def test_regression_isp_metrics(request, record_property):
    """执行ISP版本指标回归代理检查。

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
            'baseline',
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
