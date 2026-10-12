"""CAM-UW-002：水下视场角/畸变
测试大类：水下成像 / 几何变化 / P1。
目的：比较空气基线与水下图像的视场角或畸变变化，当前输出基础代理指标。
前置条件：使用真实水下图片，并提供同场景空气基线；缺少配对基线时记录N/A。
判定标准：配对输入可用时几何变化应满足CASE_LIMITS；当前单图不具备正式判定条件。
图片来源：--picture优先，其次读取images.output，最后读取images.default；由camera_case统一准备。
阈值来源：fov_change_max来自本文件CASE_LIMITS；代理阈值仅用于基础筛查，不替代标定规格。
"""

from autotest_runner import autotest

from autotest_runner.camera.advanced import evaluate

from autotest_runner.camera.execution import camera_case

CASE_LIMITS = {
    # 水下与空气视场角或畸变变化代理值的最大阈值。
    "fov_change_max": 0.2,
}

METRIC_KEYS = (
    # 记录配对输入是否可用，供N/A语义和报告复核。
    "available",
    # 记录水下图与空气基线的几何变化代理值。
    "baseline_delta",
)

def check(metrics, limits, expected_size):
    """按水下几何变化代理规则返回判定结果和中文原因。

    当前只有单张水下图，没有空气基线配对，因此保留N/A语义并返回未通过。
    该结果不是产品质量失败，也不伪造代理算法的PASS。
    """
    ok = False
    reason = "需要配置空气基线；当前camera_case仅提供单张水下图，结果为N/A"
    return ok, reason

@autotest(
    case_id='CAM-UW-002',
    title='CAM-UW-002 水下视场角/畸变',
    priority="P1",
    test_class='水下画质 / Underwater IQ',
    description=(
        '使用代理几何算法比较水下图与空气基线；当前仅有单图输入，'
        '因此明确记录N/A，不代表正式产品视场角或畸变验收。'
    ),
    expected_result=(
        '提供规定的空气基线配对输入后，几何变化代理值应满足阈值；'
        '缺少配对输入时保持N/A语义。'
    ),
    parameters=CASE_LIMITS,
)
def test_underwater_fov_distortion(request, record_property):
    """执行水下视场角和畸变代理检查。

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
