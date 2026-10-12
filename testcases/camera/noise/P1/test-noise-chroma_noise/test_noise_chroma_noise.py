"""CAM-NOISE-002：色度噪声
测试大类：噪声 / Camera IQ / P1。
目的：验证单帧输入的色度噪声，并输出可复核的代理指标。
前置条件：使用真实图片；缺少连续帧、标定卡或基线时记录N/A，不伪造PASS。
判定标准：色度噪声不超过CASE_LIMITS中的上限；该结果仅用于基础代理筛查。
图片来源：camera_case按--picture优先，其次读取配置中的images.output，最后使用images.default。
阈值来源：本文件CASE_LIMITS定义代理阈值；正式产品阈值需由标定输入确认。
"""

from autotest_runner import autotest

from autotest_runner.camera.advanced import evaluate

from autotest_runner.camera.execution import camera_case

CASE_LIMITS = {
    "chroma_noise_max": 20.0,  # chroma_noise_max 的本用例阈值。
}

METRIC_KEYS = (
    "chroma_noise",  # 记录chroma_noise，用于本用例的判定或证据。
)

def check(metrics, limits, expected_size):
    """说明本用例的输入、输出、关键指标和阈值判定。

    输入为指标字典、已合并阈值和期望尺寸；输出为通过标志及中文原因。
    关键指标由METRIC_KEYS声明，check只执行本用例代理判定，不负责生成指标。
    任一关键指标超出CASE_LIMITS或前置条件不满足时返回False；不适用输入保留N/A语义。
    """
    ok = metrics["chroma_noise"] <= limits["chroma_noise_max"]
    reason = f"色度噪声={metrics['chroma_noise']:.3f}"
    return ok, reason

@autotest(
    case_id='CAM-NOISE-002',
    title='CAM-NOISE-002 色度噪声',
    priority="P1",
    test_class='噪声与信噪比 / Noise & SNR',
    description='使用色度噪声代理算法检查真实图片；连续帧、标定卡或输入条件不足时按N/A处理，不伪造PASS。',
    expected_result='色度噪声代理指标满足CASE_LIMITS；当前结果不替代正式标定验收，输入受限时记录N/A。',
    parameters=CASE_LIMITS,
)
def test_noise_chroma_noise(request, record_property):
    """执行色度噪声代理检查。

    测试步骤依次为准备输入、计算指标、执行判定、记录证据和失败抛出异常。
    """
    # 1. 公共准备读取真实图片、输入限制和生效阈值。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 2. 调用已有公共代理算法计算指标。
        metrics = evaluate("chroma", run)
        # 3. 调用本脚本判定逻辑比较关键指标和阈值。
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 4. 保存指标、判定和证据，供报告复核。
        run.record(metrics, ok, reason, METRIC_KEYS)
        # 5. 失败时显式抛出异常，不吞掉判定结果。
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
