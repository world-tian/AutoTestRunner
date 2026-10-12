"""CAM-DEFECT-010：冻结/重复帧
测试大类：缺陷 / Camera IQ / P1。
目的：检查连续帧冻结或重复，并输出可复核的代理指标。
前置条件：至少提供两帧真实图片；单帧输入记录N/A，不伪造PASS。
判定标准：输入可用且重复相似度不超过CASE_LIMITS中的上限。
图片来源：camera_case按--picture优先，其次读取配置中的images.output，最后使用images.default。
阈值来源：本文件CASE_LIMITS定义重复帧代理阈值；正式阈值需由多帧基线确认。
"""

from autotest_runner import autotest

from autotest_runner.camera.advanced import evaluate

from autotest_runner.camera.execution import camera_case

CASE_LIMITS = {
    "duplicate_similarity_max": 0.995,  # duplicate_similarity_max 的本用例阈值。
}

METRIC_KEYS = (
    "available",  # 记录available，用于本用例的判定或证据。
    "frame_count",  # 记录frame_count，用于本用例的判定或证据。
    "duplicate_similarity",  # 记录duplicate_similarity，用于本用例的判定或证据。
)

def check(metrics, limits, expected_size):
    """说明本用例的输入、输出、关键指标和阈值判定。

    输入为指标字典、已合并阈值和期望尺寸；输出为通过标志及中文原因。
    关键指标由METRIC_KEYS声明，check只执行本用例代理判定，不负责生成指标。
    任一关键指标超出CASE_LIMITS或前置条件不满足时返回False；不适用输入保留N/A语义。
    """
    available = metrics['available']
    similarity_ok = metrics['duplicate_similarity'] <= limits['duplicate_similarity_max']
    ok = available and similarity_ok
    if not available:
        reason = '需要至少两帧；'
    else:
        reason = f"重复相似度={metrics['duplicate_similarity']:.4f}"
    return ok, reason

@autotest(
    case_id='CAM-DEFECT-010',
    title='CAM-DEFECT-010 冻结/重复帧',
    priority="P1",
    test_class='异常检测 / Defect',
    description='使用连续帧相似度代理算法检查冻结帧；少于两帧时按N/A处理，不伪造PASS。',
    expected_result='至少两帧且重复相似度代理指标满足CASE_LIMITS；正式验收需多帧基线，受限时记录N/A。',
    parameters=CASE_LIMITS,
)
def test_defect_duplicate_frame(request, record_property):
    """执行冻结或重复帧代理检查。

    测试步骤依次为准备输入、计算指标、执行判定、记录证据和失败抛出异常。
    """
    # 1. 公共准备读取真实图片、输入限制和生效阈值。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 2. 调用已有公共代理算法计算指标。
        metrics = evaluate('sequence', run)
        # 3. 调用本脚本判定逻辑比较关键指标和阈值。
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 4. 保存指标、判定和证据，供报告复核。
        run.record(metrics, ok, reason, METRIC_KEYS)
        # 5. 失败时显式抛出异常，不吞掉判定结果。
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
