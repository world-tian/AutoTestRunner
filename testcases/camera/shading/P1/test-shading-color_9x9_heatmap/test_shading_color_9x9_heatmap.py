"""CAM-SHD-004：9x9颜色均匀性
测试大类：镜头阴影 / Shading。
目的：用 9x9 网格 R/G、B/G 范围代理检查画面颜色均匀性。
前置条件：使用设备实拍、无纹理且无色块的均匀中性场；正式 shading 验收需要已验证均匀度的光源。
判定标准：R/G 和 B/G 网格范围分别不超过对应上限。
图片来源：camera_case 按 --picture 优先，其次读取 images.output，最后使用 images.default。
阈值来源：rg_range_max、bg_range_max 由本文件 CASE_LIMITS 定义，当前仅作代理筛查阈值。
"""

from autotest_runner import autotest

from autotest_runner.camera.advanced import evaluate

from autotest_runner.camera.execution import camera_case

CASE_LIMITS = {
    # 9x9 网格 R/G 范围的最大允许值。
    "rg_range_max": 0.25,
    # 9x9 网格 B/G 范围的最大允许值。
    "bg_range_max": 0.25,
}

METRIC_KEYS = (
    # 9x9 网格 R/G 范围，用于第一项阈值判定。
    "rg_range",
    # 9x9 网格 B/G 范围，用于第二项阈值判定。
    "bg_range",
    # 9x9 网格 R/G 值，用于生成热力图证据。
    "rg_grid",
    # 9x9 网格 B/G 值，用于生成热力图证据。
    "bg_grid",
)


def check(metrics, limits, expected_size):
    """执行 9x9 颜色均匀性代理判定并返回中文原因。

    输入是指标字典、已合并阈值和期望尺寸；输出是布尔判定及原因。
    本函数只比较公共网格指标与 CASE_LIMITS，不负责生成指标或热力图。
    未提供规定均匀场输入时，结果仅代表代理检查，不能用于正式验收。
    """
    rg_ok = metrics["rg_range"] <= limits["rg_range_max"]
    bg_ok = metrics["bg_range"] <= limits["bg_range_max"]
    ok = rg_ok and bg_ok
    reason = (
        f"R/G范围={metrics['rg_range']:.3f}（上限 {limits['rg_range_max']}），"
        f"B/G范围={metrics['bg_range']:.3f}（上限 {limits['bg_range_max']}）"
    )
    return ok, reason

@autotest(
    case_id="CAM-SHD-004",
    title="CAM-SHD-004 9×9颜色均匀性",
    priority="P1",
    test_class="亮度均匀性 / LSC & Shading",
    description=(
        "输出 9x9 R/G、B/G 热力图，并用网格范围执行颜色均匀性代理算法。"
        "正式验收要求设备实拍的均匀中性场；综合色卡的色块会污染全图 9×9 网格统计。"
    ),
    expected_result=(
        "R/G 和 B/G 网格范围分别不超过对应阈值。"
        "该结果仅代表基础代理检查，缺少规定输入时必须保留 N/A 语义。"
    ),
    parameters=CASE_LIMITS,
)
def test_shading_color_9x9_heatmap(request, record_property):
    """按五步流程执行 9x9 颜色均匀性基础代理检查。"""
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
