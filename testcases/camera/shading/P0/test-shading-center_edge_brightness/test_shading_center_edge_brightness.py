"""CAM-SHD-001 中心/边缘亮度差
测试大类：亮度均匀性 / LSC & Shading
目的：判断暗角及 LSC 效果
前置条件：均匀平场或积分球，锁定曝光；避免照明不均干扰
判定标准：中心对每个角落的最大相对亮度差 ≤ 0.30，且中心及四角平均亮度均 ≥ 60。
图片来源：默认读取 camera/config.json 的 images.shading，未配置时读取 images.default；
          单次运行的 --picture 优先级最高。CAMERA_CONFIG 仅用于指定另一份 config.json。
阈值来源：相对差上限 center_edge_max=0.30 在本脚本 CASE_LIMITS；有效亮度下限 mean_min=60 在 camera/common.json。
"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import shading_metrics


# 本用例独立维护判定；只有多用例复用的阈值来自 camera/common.json。
# center_edge_max：中心与最偏离角落的相对亮度差上限；最低有效亮度见 common.json。
CASE_LIMITS = {"center_edge_max":0.3}


METRIC_KEYS = ("center_edge_delta", "roi_luma")  # 终端与报告只展示本用例关心的实测指标。


def check(m, limits, expected_size):
    """返回本用例判定结果和包含实测值的中文原因。"""
    delta = m['center_edge_delta']
    minimum = min(m['roi_luma'].values())
    ok = delta <= limits['center_edge_max'] and minimum >= limits['mean_min']
    return ok, f"中心/边缘亮度差={delta:.3f}，要求 ≤ {limits['center_edge_max']}；区域最低亮度={minimum:.2f}，要求 ≥ {limits['mean_min']}"


@autotest(case_id="CAM-SHD-001", title="CAM-SHD-001 中心/边缘亮度差", priority="P0", test_class="亮度均匀性 / LSC & Shading",
          description="中心/边缘亮度差；判定标准：中心对每个角落的最大相对亮度差 ≤ 0.30，且中心及四角平均亮度均 ≥ 60。",
          expected_result="中心对每个角落的最大相对亮度差 ≤ 0.30，且中心及四角平均亮度均 ≥ 60。",
          parameters={"center_edge_max":0.3,"mean_min":60})
def test_shading_center_edge_brightness(request, record_property):
    # 1. 公共准备只负责加载真实图片与阈值；编号来自 @autotest 元数据。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 2. 明确调用本用例需要的公共指标函数，再调用上方独立判定。
        metrics = shading_metrics(run.rgb)
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 3. 记录实测值和判定，失败时在本脚本显式抛出异常。
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
