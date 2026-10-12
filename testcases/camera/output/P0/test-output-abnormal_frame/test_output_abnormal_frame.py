"""CAM-IMG-003 全黑/全白/严重异常图像
测试大类：基础图像 / Output
目的：筛查全黑、全白或亮度几乎不变化的异常输出；不能覆盖花屏、坏点等其他缺陷。
前置条件：使用正常照明、有明暗变化的实际相机输出图，支持 8-bit JPEG/PNG。
判定标准：Y≤10 的像素占比 < 0.98；Y≥245 的像素占比 < 0.98；全图 Y 标准差 ≥ 1。
图片来源：默认读取 camera/config.json 的 images.output，未配置时读取 images.default；
          单次运行的 --picture 优先级最高。CAMERA_CONFIG 仅用于指定另一份 config.json。
阈值来源：本用例的两项判定阈值均定义在下方 CASE_LIMITS，不依赖 camera/common.json。
"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import exposure_metrics


# 本用例独立维护判定；只有多用例复用的阈值来自 camera/common.json。
# extreme_max：极暗或极亮像素占比的严格上限；std_min：全图亮度标准差下限。
CASE_LIMITS = {
    "extreme_max": 0.98,  # 极暗、极亮像素各自占全图的比例必须严格小于 98%
    "std_min": 1,         # 全图 8-bit 亮度 Y 的标准差至少为 1，排除近乎恒定的画面
}


METRIC_KEYS = ("under_ratio", "over_ratio", "std_luma")  # 终端与报告只展示本用例关心的实测指标。


def check(m, limits, expected_size):
    """返回本用例判定结果和包含实测值的中文原因。"""
    ok = m['under_ratio'] < limits['extreme_max'] and m['over_ratio'] < limits['extreme_max'] and m['std_luma'] >= limits['std_min']
    return ok, f"暗部比例={m['under_ratio']:.3f}、亮部比例={m['over_ratio']:.3f}，均需 < {limits['extreme_max']}；亮度标准差={m['std_luma']:.2f}，需 ≥ {limits['std_min']}"


@autotest(case_id="CAM-IMG-003", title="CAM-IMG-003 全黑/全白/严重异常图像", priority="P0", test_class="基础图像 / Output",
          description="筛查全黑、全白或亮度近乎恒定：Y≤10 和 Y≥245 的像素占比各 < 0.98，亮度标准差 ≥ 1",
          expected_result="暗像素占比 < 0.98，亮像素占比 < 0.98，亮度标准差 ≥ 1",
          parameters={"dark_pixel_y_max": 10, "bright_pixel_y_min": 245,
                      "extreme_max": 0.98, "std_min": 1})

def test_output_abnormal_frame(request, record_property):
    # 1. 公共准备只负责加载真实图片与阈值；编号来自 @autotest 元数据。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 2. 明确调用本用例需要的公共指标函数，再调用上方独立判定。
        metrics = exposure_metrics(run.rgb)
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 3. 记录实测值和判定，失败时在本脚本显式抛出异常。
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
