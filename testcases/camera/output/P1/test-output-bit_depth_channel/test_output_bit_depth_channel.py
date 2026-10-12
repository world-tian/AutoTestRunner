"""CAM-IMG-005 位深与通道
测试大类：基础图像 / Output
目的：确认输出是支持的8-bit RGB/RGBA图片。
"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import output_format_metrics

CASE_LIMITS = {"bit_depth": 8, "channels_min": 3, "channels_max": 4}
METRIC_KEYS = ("format", "mode", "channels", "bit_depth")


def check(metrics, limits, expected_size):
    ok = (metrics["bit_depth"] == limits["bit_depth"] and
          limits["channels_min"] <= metrics["channels"] <= limits["channels_max"])
    return ok, f"格式={metrics['format']}、模式={metrics['mode']}、位深={metrics['bit_depth']}、通道={metrics['channels']}"


@autotest(case_id="CAM-IMG-005", title="CAM-IMG-005 位深与通道", priority="P1", test_class="基础图像 / Output",
          description="检查输出是否为支持的8-bit RGB/RGBA图片。",
          expected_result="位深为8，通道为3或4。", parameters=CASE_LIMITS)
def test_output_bit_depth_channel(request, record_property):
    with camera_case(request, record_property, CASE_LIMITS) as run:
        metrics = output_format_metrics(run.image_path)
        ok, reason = check(metrics, run.limits, run.expected_size)
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
