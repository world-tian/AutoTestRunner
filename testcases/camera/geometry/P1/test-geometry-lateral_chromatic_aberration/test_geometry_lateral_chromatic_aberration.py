"""CAM-GEO-002：横向色差LCA
测试大类：几何 / Camera IQ / P1。
目的：验证横向色差LCA，并输出可复核的代理指标。
前置条件：使用真实图片；缺少标定卡或基线时记录N/A，不伪造PASS。
判定标准：横向色差代理指标不超过CASE_LIMITS中的上限。
图片来源：camera_case按--picture优先，其次读取配置中的images.output，最后使用images.default。
阈值来源：本文件CASE_LIMITS定义代理阈值；正式产品阈值需由标定输入确认。
"""

from autotest_runner import autotest

from autotest_runner.camera.advanced import evaluate

from autotest_runner.camera.execution import camera_case

CASE_LIMITS = {
    "lca_max": 20.0,  # lca_max 的本用例阈值。
}

METRIC_KEYS = (
    "lateral_chromatic_aberration",  # 记录lateral_chromatic_aberration，用于本用例的判定或证据。
)

def check(metrics, limits, expected_size):
    """说明本用例的输入、输出、关键指标和阈值判定。

    输入为指标字典、已合并阈值和期望尺寸；输出为通过标志及中文原因。
    关键指标由METRIC_KEYS声明，check只执行本用例代理判定，不负责生成指标。
    任一关键指标超出CASE_LIMITS或前置条件不满足时返回False；不适用输入保留N/A语义。
    """
    ok = metrics["lateral_chromatic_aberration"] <= limits["lca_max"]
    reason = f"横向色差代理={metrics['lateral_chromatic_aberration']:.3f}"
    return ok, reason

@autotest(
    case_id='CAM-GEO-002',
    title='CAM-GEO-002 横向色差LCA',
    priority="P1",
    test_class='几何 / Geometry',
    description='使用横向色差LCA代理算法检查真实图片；标定输入不足时按N/A处理，不伪造PASS。',
    expected_result='横向色差LCA代理指标满足CASE_LIMITS；正式验收需标定输入，受限时记录N/A。',
    parameters=CASE_LIMITS,
)
def test_geometry_lateral_chromatic_aberration(request, record_property):
    """执行横向色差代理检查。

    测试步骤依次为准备输入、计算指标、执行判定、记录证据和失败抛出异常。
    """
    # 1. 公共准备读取真实图片、输入限制和生效阈值。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 2. 调用已有公共代理算法计算指标。
        metrics = evaluate("geometry", run)
        # 3. 调用本脚本判定逻辑比较关键指标和阈值。
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 4. 保存指标、判定和证据，供报告复核。
        run.record(metrics, ok, reason, METRIC_KEYS)
        # 5. 失败时显式抛出异常，不吞掉判定结果。
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
