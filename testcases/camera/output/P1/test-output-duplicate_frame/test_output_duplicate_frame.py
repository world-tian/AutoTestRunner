"""CAM-IMG-006：重复帧/冻结
测试大类：输出质量 / 图像异常。
目的：使用重复相似度代理检查连续输出是否出现重复帧或冻结。
前置条件：提供至少两帧真实输出；缺少连续帧、标定卡或基线时记录 N/A。
判定标准：重复相似度不超过 duplicate_similarity_max，且连续帧输入可用。
图片来源：camera_case 按 --picture 优先，其次读取 images.output，最后使用 images.default。
阈值来源：duplicate_similarity_max 由本文件 CASE_LIMITS 定义，属于基础代理筛查阈值。
"""

from autotest_runner import autotest

from autotest_runner.camera.advanced import evaluate

from autotest_runner.camera.execution import camera_case

CASE_LIMITS = {
    # 连续帧重复相似度的最大允许值；超过该值判定为疑似冻结。
    "duplicate_similarity_max": 0.995,
}

METRIC_KEYS = (
    # 输入是否满足至少两帧的前置条件，用于保留 N/A 语义。
    "available",
    # 实际参与代理判定的帧数量，用于报告复核。
    "frame_count",
    # 连续帧之间的重复相似度，用于和 duplicate_similarity_max 比较。
    "duplicate_similarity",
)


def check(metrics, limits, expected_size):
    """执行重复帧代理判定并返回通过标志和中文原因。

    输入是指标字典、已合并阈值和期望尺寸；输出是布尔判定及原因。
    本函数只比较公共代理算法输出与 CASE_LIMITS，不负责生成指标。
    少于两帧时保留 N/A 语义，不将不适用输入伪报为通过。
    """
    if not metrics['available']:
        return False, "输入不适用（N/A）：需要至少两帧真实输出。"

    similarity_ok = metrics["duplicate_similarity"] <= limits["duplicate_similarity_max"]
    if not similarity_ok:
        reason = (
            f"帧数={metrics['frame_count']}，重复相似度="
            f"{metrics['duplicate_similarity']:.4f}，超过上限 "
            f"{limits['duplicate_similarity_max']}"
        )
        return False, reason

    reason = (
        f"帧数={metrics['frame_count']}，重复相似度="
        f"{metrics['duplicate_similarity']:.4f}，不超过上限 "
        f"{limits['duplicate_similarity_max']}"
    )
    return True, reason

@autotest(
    case_id="CAM-IMG-006",
    title="CAM-IMG-006 重复帧/冻结",
    priority="P1",
    test_class="基础图像 / Output",
    description=(
        "使用连续帧重复相似度进行冻结代理检查；要求至少两帧真实输出。"
        "该实现是基础代理算法，缺少连续帧、标定卡或基线时输入限制不满足。"
    ),
    expected_result=(
        "输入满足至少两帧时，重复相似度不超过 duplicate_similarity_max。"
        "输入限制不满足时记录 N/A，不将代理结果解释为正式产品验收结论。"
    ),
    parameters=CASE_LIMITS,
)
def test_output_duplicate_frame(request, record_property):
    """按五步流程执行重复帧/冻结代理检查。"""
    # 第一步：准备真实图片、输入限制和生效阈值。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 第二步：调用公共重复帧代理算法计算指标。
        metrics = evaluate('sequence', run)
        # 第三步：调用本脚本判定逻辑比较指标和阈值。
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 第四步：保存指标、判定和证据，供报告复核。
        run.record(metrics, ok, reason, METRIC_KEYS)
        # 第五步：失败时显式抛出异常，不吞掉判定结果。
        if ok is False:
            raise AssertionError(f"{run.case_id}: {reason}")
