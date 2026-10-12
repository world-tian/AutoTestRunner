"""CAM-DEFECT-009：帧损坏
测试大类：缺陷 / Camera IQ / P1。
目的：检查当前帧是否可解码且尺寸符合预期，并输出代理指标。
前置条件：使用真实图片；缺少规定尺寸或输入条件时记录N/A，不伪造PASS。
判定标准：图像能够解码，且宽高与camera_case提供的expected_size一致。
图片来源：camera_case按--picture优先，其次读取配置中的images.output，最后使用images.default。
阈值来源：本用例无额外CASE_LIMITS阈值，尺寸要求来自camera_case的输入配置。
"""

from autotest_runner import autotest

from autotest_runner.camera.metrics import image_size

from autotest_runner.camera.execution import camera_case

CASE_LIMITS = {
    # 本用例使用camera_case提供的期望尺寸，不增加专用数值阈值。
}

METRIC_KEYS = (
    "width",  # 记录width，用于本用例的判定或证据。
    "height",  # 记录height，用于本用例的判定或证据。
)

def check(metrics, limits, expected_size):
    """说明本用例的输入、输出、关键指标和阈值判定。

    输入为指标字典、已合并阈值和期望尺寸；输出为通过标志及中文原因。
    关键指标由METRIC_KEYS声明，check只执行本用例代理判定，不负责生成指标。
    任一关键指标超出CASE_LIMITS或前置条件不满足时返回False；不适用输入保留N/A语义。
    """
    ok = [metrics['width'], metrics['height']] == expected_size
    reason = f"解码尺寸={metrics['width']}x{metrics['height']}，期望={expected_size}"
    return ok, reason

@autotest(
    case_id='CAM-DEFECT-009',
    title='CAM-DEFECT-009 帧损坏',
    priority="P1",
    test_class='异常检测 / Defect',
    description='使用图像解码和尺寸代理算法检查真实帧；输入限制不满足时按N/A处理，不伪造PASS。',
    expected_result='帧可完整解码且尺寸符合expected_size；正式验收需规定输入，受限时记录N/A。',
    parameters=CASE_LIMITS,
)
def test_defect_frame_corruption(request, record_property):
    """执行帧损坏代理检查。

    测试步骤依次为准备输入、计算指标、执行判定、记录证据和失败抛出异常。
    """
    # 1. 公共准备读取真实图片、输入限制和生效阈值。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 2. 调用已有公共代理算法计算指标。
        metrics = image_size(run.rgb)
        # 3. 调用本脚本判定逻辑比较关键指标和阈值。
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 4. 保存指标、判定和证据，供报告复核。
        run.record(metrics, ok, reason, METRIC_KEYS)
        # 5. 失败时显式抛出异常，不吞掉判定结果。
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
