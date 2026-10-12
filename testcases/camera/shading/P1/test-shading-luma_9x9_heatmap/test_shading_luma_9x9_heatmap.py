"""CAM-SHD-003：9x9亮度均匀性
测试大类：镜头阴影 / Shading。
目的：用 9x9 网格亮度范围代理检查画面亮度均匀性。
前置条件：使用真实均匀场图片；正式 shading 验收需要已标定的均匀场输入。
判定标准：luma_range 代理指标不超过 luma_range_max。
图片来源：camera_case 按 --picture 优先，其次读取 images.output，最后使用 images.default。
阈值来源：luma_range_max 由本文件 CASE_LIMITS 定义，当前仅作基础代理筛查阈值。
"""

from autotest_runner import autotest

from autotest_runner.camera.advanced import evaluate

from autotest_runner.camera.execution import camera_case

CASE_LIMITS = {
    # 9x9 网格亮度范围的最大允许值，正式阈值需由均匀场标定确认。
    "luma_range_max": 60.0,
}

METRIC_KEYS = (
    # 9x9 网格亮度最大值与最小值之差，用于阈值判定。
    "luma_range",
    # 9x9 网格亮度值，用于生成证据和定位不均匀区域。
    "luma_grid",
)


def check(metrics, limits, expected_size):
    """执行 9x9 亮度均匀性代理判定并返回中文原因。

    输入是指标字典、已合并阈值和期望尺寸；输出是布尔判定及原因。
    本函数只比较公共网格指标与 CASE_LIMITS，不负责生成指标或热力图。
    未提供均匀场标定输入时，结果仅代表基础代理检查并保留 N/A 语义。
    """
    value = metrics["luma_range"]
    ok = value <= limits["luma_range_max"]
    if ok:
        reason = f"9x9亮度范围={value:.3f}，不超过上限 {limits['luma_range_max']}"
    else:
        reason = f"9x9亮度范围={value:.3f}，超过上限 {limits['luma_range_max']}"
    return ok, reason

@autotest(
    case_id="CAM-SHD-003",
    title="CAM-SHD-003 9×9亮度均匀性",
    priority="P1",
    test_class="亮度均匀性 / LSC & Shading",
    description=(
        "输出 9x9 亮度热力图，并用网格亮度范围执行均匀性代理算法。"
        "正式验收要求均匀场标定输入；输入限制不满足时记录 N/A。"
    ),
    expected_result=(
        "luma_range 代理值不超过 luma_range_max。"
        "缺少均匀场标定输入时仅记录基础代理结果，并保留 N/A 语义。"
    ),
    parameters=CASE_LIMITS,
)
def test_shading_luma_9x9_heatmap(request, record_property):
    """按五步流程执行 9x9 亮度均匀性基础代理检查。"""
    # 第一步：准备真实图片、输入限制和生效阈值。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 第二步：调用公共 9x9 网格代理算法计算指标。
        metrics = evaluate('grid', run)
        # 第三步：调用本脚本判定逻辑比较指标和阈值。
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 第四步：保存指标、判定和证据，供报告复核。
        run.record(metrics, ok, reason, METRIC_KEYS)
        # 第五步：失败时显式抛出异常，不吞掉判定结果。
        if ok is False:
            raise AssertionError(f"{run.case_id}: {reason}")
