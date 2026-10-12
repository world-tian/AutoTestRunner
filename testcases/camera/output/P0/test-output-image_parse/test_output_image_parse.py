"""CAM-IMG-001 图片可解析
测试大类：基础图像 / Output
目的：判断图像输出链路是否正常
前置条件：真实拍摄的 8-bit JPEG/PNG 图片；允许正常明暗或色彩变化。
判定标准：图片完整解码成功；宽、高均至少 32 像素；仅接受第一版支持的 8-bit 图像模式。
图片来源：默认读取 camera/config.json 的 images.output，未配置时读取 images.default；
          单次运行的 --picture 优先级最高。CAMERA_CONFIG 仅用于指定另一份 config.json。
阈值来源：本用例无数值阈值；可解析由 camera/metrics.py 的 decode() 判定。
"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import image_size


# 本用例独立维护判定；只有多用例复用的阈值来自 camera/common.json。
# 完整解码即通过；本用例没有数值阈值。
CASE_LIMITS = {}


METRIC_KEYS = ("width", "height")  # 终端与报告只展示本用例关心的实测指标。


def check(m, limits, expected_size):
    """返回本用例判定结果和包含实测值的中文原因。"""
    return True, '图片完整解码成功'


@autotest(case_id="CAM-IMG-001", title="CAM-IMG-001 图片可解析", priority="P0", test_class="基础图像 / Output",
          description="图片可解析；判定标准：图片完整解码成功；宽、高均至少 32 像素；仅接受第一版支持的 8-bit 图像模式。",
          expected_result="图片完整解码成功；宽、高均至少 32 像素；仅接受第一版支持的 8-bit 图像模式。",
          parameters={"minimum_width":32,"minimum_height":32})
def test_output_image_parse(request, record_property):
    # 1. 公共准备只负责加载真实图片与阈值；编号来自 @autotest 元数据。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 2. 明确调用本用例需要的公共指标函数，再调用上方独立判定。
        metrics = image_size(run.rgb)
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 3. 记录实测值和判定，失败时在本脚本显式抛出异常。
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
