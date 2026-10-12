"""CAM-IMG-002 分辨率检查
测试大类：基础图像 / Output
目的：验证输出规格是否符合要求
前置条件：真实拍摄的 8-bit JPEG/PNG 图片；需明确本次输出规格。
判定标准：按 EXIF 方向校正后，宽×高等于 config.json.expected_size；当前默认值为 512×512。
图片来源：默认读取 camera/config.json 的 images.output，未配置时读取 images.default；
          单次运行的 --picture 优先级最高。CAMERA_CONFIG 仅用于指定另一份 config.json。
阈值来源：尺寸目标在 camera/config.json 的 expected_size；本脚本 CASE_LIMITS 为空。
"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import image_size


# 本用例独立维护判定；只有多用例复用的阈值来自 camera/common.json。
# 尺寸由 camera/config.json 的 expected_size [宽, 高] 指定。
CASE_LIMITS = {}


METRIC_KEYS = ("width", "height")  # 终端与报告只展示本用例关心的实测指标。


def check(m, limits, expected_size):
    """返回本用例判定结果和包含实测值的中文原因。"""
    actual = [m['width'], m['height']]
    return actual == expected_size, f'实际尺寸 {actual}，要求 {expected_size}'


@autotest(case_id="CAM-IMG-002", title="CAM-IMG-002 分辨率检查", priority="P0", test_class="基础图像 / Output",
          description="分辨率检查；判定标准：按 EXIF 方向校正后，宽×高等于 config.json.expected_size；当前默认值为 512×512。",
          expected_result="按 EXIF 方向校正后，宽×高等于 config.json.expected_size；当前默认值为 512×512。",
          parameters={"expected_size":"config.json.expected_size","default_size":[512,512]})
def test_output_output_resolution(request, record_property):
    # 1. 公共准备只负责加载真实图片与阈值；编号来自 @autotest 元数据。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 2. 明确调用本用例需要的公共指标函数，再调用上方独立判定。
        metrics = image_size(run.rgb)
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 3. 记录实测值和判定，失败时在本脚本显式抛出异常。
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
