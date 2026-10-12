"""CAM-DEFECT-004 大面积异常色块/花屏检测
测试大类：异常检测 / Defect
目的：发现中性均匀场中的大面积局部色块；不代表能检出所有花屏、坏点或条纹。
前置条件：中性均匀场，仅针对大面积局部色度异常；非通用花屏或坏点检测
判定标准：中性均匀场的 8×8 分块最大局部色度残差均值 ≤ 25；仅检测较大的局部异常色块。
图片来源：默认读取 camera/config.json 的 images.defect，未配置时读取 images.default；
          单次运行的 --picture 优先级最高。CAMERA_CONFIG 仅用于指定另一份 config.json。
阈值来源：上限 chroma_tile_max=25 在本脚本 CASE_LIMITS；本用例不使用 common.json 的共享判定阈值。
"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import defect_metrics


# 本用例独立维护判定；只有多用例复用的阈值来自 camera/common.json。
# chroma_tile_max：8×8 分块中色度异常块均值的上限，仅适合中性场。
CASE_LIMITS = {"chroma_tile_max":25}


METRIC_KEYS = ("max_chroma_tile",)  # 终端与报告只展示本用例关心的实测指标。


def check(m, limits, expected_size):
    """返回本用例判定结果和包含实测值的中文原因。"""
    v = m['max_chroma_tile']
    return v <= limits['chroma_tile_max'], f"最大色度异常块={v:.2f}，要求 ≤ {limits['chroma_tile_max']}"


@autotest(case_id="CAM-DEFECT-004", title="CAM-DEFECT-004 大面积异常色块/花屏检测", priority="P0", test_class="异常检测 / Defect",
          description="大面积异常色块/花屏检测；判定标准：中性均匀场的 8×8 分块最大局部色度残差均值 ≤ 25；仅检测较大的局部异常色块。",
          expected_result="中性均匀场的 8×8 分块最大局部色度残差均值 ≤ 25；仅检测较大的局部异常色块。",
          parameters={"grid_rows":8,"grid_cols":8,"chroma_tile_max":25})
def test_defect_large_color_block(request, record_property):
    # 1. 公共准备只负责加载真实图片与阈值；编号来自 @autotest 元数据。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 2. 明确调用本用例需要的公共指标函数，再调用上方独立判定。
        metrics = defect_metrics(run.rgb)
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 3. 记录实测值和判定，失败时在本脚本显式抛出异常。
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
