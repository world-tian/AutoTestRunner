"""CAM-SHP-009：角落/中心MTF比
测试大类：清晰度 / MTF。
目的：用中心与四角清晰度比值代理检查画面边缘清晰度保持能力。
前置条件：使用真实纹理图片；正式 MTF 比值验收需要 ISO12233 或等效标定输入。
判定标准：sharpness_ratio 不低于 corner_center_mtf_ratio_min。
图片来源：camera_case 按 --picture 优先，其次读取 images.output，最后使用 images.default。
阈值来源：corner_center_mtf_ratio_min 由本文件 CASE_LIMITS 定义，当前仅作代理筛查阈值。
"""

from autotest_runner import autotest

from autotest_runner.camera.advanced import evaluate

from autotest_runner.camera.execution import camera_case

CASE_LIMITS = {
    # 角落与中心清晰度代理比值的最小允许值。
    "corner_center_mtf_ratio_min": 0.4,
}

METRIC_KEYS = (
    # 角落与中心清晰度的代理比值，用于阈值判定。
    "sharpness_ratio",
    # 各 ROI 清晰度结果，用于报告复核和定位差异。
    "roi_sharpness",
)


def check(metrics, limits, expected_size):
    """执行角落/中心清晰度比代理判定并返回中文原因。

    输入是指标字典、已合并阈值和期望尺寸；输出是布尔判定及原因。
    本函数只比较公共 ROI 清晰度代理结果与 CASE_LIMITS，不负责生成指标。
    缺少规定标定输入时，结果仅保留基础代理检查和 N/A 语义。
    """
    value = metrics["sharpness_ratio"]
    ok = value >= limits["corner_center_mtf_ratio_min"]
    if ok:
        reason = f"角落/中心代理比={value:.3f}，达到下限 {limits['corner_center_mtf_ratio_min']}"
    else:
        reason = f"角落/中心代理比={value:.3f}，低于下限 {limits['corner_center_mtf_ratio_min']}"
    return ok, reason

@autotest(
    case_id="CAM-SHP-009",
    title="CAM-SHP-009 角落/中心MTF比",
    priority="P1",
    test_class="清晰度 / Sharpness",
    description=(
        "比较中心和四角清晰度，使用 ROI 清晰度比作为 MTF 均匀性的代理算法。"
        "正式验收需要标定输入；输入限制不满足时记录 N/A。"
    ),
    expected_result=(
        "sharpness_ratio 代理值达到 corner_center_mtf_ratio_min。"
        "该结果仅代表基础代理检查，缺少规定标定输入时必须保留 N/A 语义。"
    ),
    parameters=CASE_LIMITS,
)
def test_sharpness_corner_center_mtf_ratio(request, record_property):
    """按五步流程执行角落/中心 MTF 比基础代理检查。"""
    # 第一步：准备真实图片、输入限制和生效阈值。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 第二步：调用公共 ROI 清晰度代理算法计算指标。
        metrics = evaluate('sharpness', run)
        # 第三步：调用本脚本判定逻辑比较指标和阈值。
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 第四步：保存指标、判定和证据，供报告复核。
        run.record(metrics, ok, reason, METRIC_KEYS)
        # 第五步：失败时显式抛出异常，不吞掉判定结果。
        if ok is False:
            raise AssertionError(f"{run.case_id}: {reason}")
