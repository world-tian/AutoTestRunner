"""CAM-SHP-007：MTF50基础代理
测试大类：清晰度 / MTF。
目的：用全局 Laplacian 清晰度代理检查 MTF50 的基础水平。
前置条件：使用真实纹理图片；正式 MTF50 验收需要 ISO12233 标定输入。
判定标准：global_sharpness 代理指标不低于 mtf50_min。
图片来源：camera_case 按 --picture 优先，其次读取 images.output，最后使用 images.default。
阈值来源：mtf50_min 由本文件 CASE_LIMITS 定义，当前仅作代理筛查阈值。
"""

from autotest_runner import autotest

from autotest_runner.camera.advanced import evaluate

from autotest_runner.camera.execution import camera_case

CASE_LIMITS = {
    # MTF50 基础代理的最小允许值，正式阈值需由标定数据确认。
    "mtf50_min": 80.0,
}

METRIC_KEYS = (
    # 全图 Laplacian 清晰度结果，作为 MTF50 的基础代理指标。
    "global_sharpness",
)


def check(metrics, limits, expected_size):
    """执行 MTF50 基础代理判定并返回中文原因。

    输入是指标字典、已合并阈值和期望尺寸；输出是布尔判定及原因。
    本函数只比较公共清晰度代理结果与 CASE_LIMITS，不负责生成指标。
    未提供 ISO12233 标定输入时，结果仅表示基础代理检查而非正式 MTF 结论。
    """
    value = metrics["global_sharpness"]
    ok = value >= limits["mtf50_min"]
    if ok:
        reason = f"MTF50代理={value:.3f}，达到下限 {limits['mtf50_min']}"
    else:
        reason = f"MTF50代理={value:.3f}，低于下限 {limits['mtf50_min']}"
    return ok, reason

@autotest(
    case_id="CAM-SHP-007",
    title="CAM-SHP-007 MTF50基础代理",
    priority="P1",
    test_class="清晰度 / Sharpness",
    description=(
        "使用全局 Laplacian 清晰度作为 MTF50 代理算法；正式验收要求 ISO12233 标定输入。"
        "输入限制不满足时记录 N/A，不将基础代理结果解释为正式 MTF50 结论。"
    ),
    expected_result=(
        "global_sharpness 代理值达到 mtf50_min。"
        "缺少 ISO12233 标定输入时仅记录代理检查结果，并保留 N/A 语义。"
    ),
    parameters=CASE_LIMITS,
)
def test_sharpness_mtf50(request, record_property):
    """按五步流程执行 MTF50 基础代理检查。"""
    # 第一步：准备真实图片、输入限制和生效阈值。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 第二步：调用公共清晰度代理算法计算指标。
        metrics = evaluate('sharpness', run)
        # 第三步：调用本脚本判定逻辑比较指标和阈值。
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 第四步：保存指标、判定和证据，供报告复核。
        run.record(metrics, ok, reason, METRIC_KEYS)
        # 第五步：失败时显式抛出异常，不吞掉判定结果。
        if ok is False:
            raise AssertionError(f"{run.case_id}: {reason}")
