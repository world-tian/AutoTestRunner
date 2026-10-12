"""CAM-NOISE-003：信噪比
测试大类：噪声 / Camera IQ / P1。
目的：验证线性信噪比和分贝信噪比，并输出可复核的代理指标。
前置条件：使用真实图片；连续帧、标定卡或基线不可用时记录N/A。
判定标准：线性信噪比和分贝信噪比分别不低于CASE_LIMITS中的下限。
图片来源：camera_case按--picture优先，其次读取配置中的images.output，最后使用images.default。
阈值来源：本文件CASE_LIMITS定义信噪比代理阈值；正式阈值需由标定输入确认。
"""

from autotest_runner import autotest

from autotest_runner.camera.advanced import evaluate

from autotest_runner.camera.execution import camera_case

CASE_LIMITS = {
    "snr_min": 8.0,  # snr_min 的本用例阈值。
    "snr_db_min": 18.0,  # snr_db_min 的本用例阈值。
}

METRIC_KEYS = (
    "signal_to_noise_ratio",  # 记录signal_to_noise_ratio，用于本用例的判定或证据。
    "snr_db",  # 记录snr_db，用于本用例的判定或证据。
)

def check(metrics, limits, expected_size):
    """说明本用例的输入、输出、关键指标和阈值判定。

    输入为指标字典、已合并阈值和期望尺寸；输出为通过标志及中文原因。
    关键指标由METRIC_KEYS声明，check只执行本用例代理判定，不负责生成指标。
    任一关键指标超出CASE_LIMITS或前置条件不满足时返回False；不适用输入保留N/A语义。
    """
    snr_ok = metrics["signal_to_noise_ratio"] >= limits["snr_min"]
    snr_db_ok = metrics["snr_db"] >= limits["snr_db_min"]
    ok = snr_ok and snr_db_ok
    reason = f"SNR={metrics['signal_to_noise_ratio']:.3f}，SNR(dB)={metrics['snr_db']:.3f}"
    return ok, reason

@autotest(
    case_id='CAM-NOISE-003',
    title='CAM-NOISE-003 信噪比',
    priority="P1",
    test_class='噪声与信噪比 / Noise & SNR',
    description='使用线性和分贝信噪比代理算法检查真实图片；输入条件不足时按N/A处理，不伪造PASS。',
    expected_result='线性与分贝信噪比代理指标均满足CASE_LIMITS；正式验收需标定输入，受限时记录N/A。',
    parameters=CASE_LIMITS,
)
def test_noise_signal_to_noise_ratio(request, record_property):
    """执行信噪比代理检查。

    测试步骤依次为准备输入、计算指标、执行判定、记录证据和失败抛出异常。
    """
    # 1. 公共准备读取真实图片、输入限制和生效阈值。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 2. 调用已有公共代理算法计算指标。
        metrics = evaluate("snr", run)
        # 3. 调用本脚本判定逻辑比较关键指标和阈值。
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 4. 保存指标、判定和证据，供报告复核。
        run.record(metrics, ok, reason, METRIC_KEYS)
        # 5. 失败时显式抛出异常，不吞掉判定结果。
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
