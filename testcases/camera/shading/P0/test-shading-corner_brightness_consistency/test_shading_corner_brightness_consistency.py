"""CAM-SHD-002 四角亮度一致性
测试大类：亮度均匀性 / LSC & Shading
目的：判断局部 Shading 或装配异常
前置条件：均匀平场或积分球，锁定曝光；避免照明不均干扰
判定标准：四角亮度（最大值−最小值）/四角均值 ≤ 0.20，且中心及四角平均亮度均 ≥ 60。
图片来源：默认读取 camera/config.json 的 images.shading，未配置时读取 images.default；
          单次运行的 --picture 优先级最高。CAMERA_CONFIG 仅用于指定另一份 config.json。
阈值来源：相对差上限 corner_delta_max=0.20 在本脚本 CASE_LIMITS；有效亮度下限 mean_min=60 在 camera/common.json。
"""
from autotest_runner import autotest
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import shading_metrics


# 本用例独立维护判定；只有多用例复用的阈值来自 camera/common.json。
# corner_delta_max：四角最大/最小亮度极差相对均值的上限。
CASE_LIMITS = {"corner_delta_max":0.2}


METRIC_KEYS = ("corner_delta", "roi_luma")  # 终端与报告只展示本用例关心的实测指标。


def check(m, limits, expected_size):
    """返回本用例判定结果和包含实测值的中文原因。"""
    delta = m['corner_delta']
    minimum = min(m['roi_luma'].values())
    ok = delta <= limits['corner_delta_max'] and minimum >= limits['mean_min']
    return ok, f"四角亮度差={delta:.3f}，要求 ≤ {limits['corner_delta_max']}；区域最低亮度={minimum:.2f}，要求 ≥ {limits['mean_min']}"


@autotest(case_id="CAM-SHD-002", title="CAM-SHD-002 四角亮度一致性", priority="P0", test_class="亮度均匀性 / LSC & Shading",
          description="四角亮度一致性；判定标准：四角亮度（最大值−最小值）/四角均值 ≤ 0.20，且中心及四角平均亮度均 ≥ 60。",
          expected_result="四角亮度（最大值−最小值）/四角均值 ≤ 0.20，且中心及四角平均亮度均 ≥ 60。",
          parameters={"corner_delta_max":0.2,"mean_min":60})
def test_shading_corner_brightness_consistency(request, record_property):
    # 1. 公共准备只负责加载真实图片与阈值；编号来自 @autotest 元数据。
    with camera_case(request, record_property, CASE_LIMITS) as run:
        # 2. 明确调用本用例需要的公共指标函数，再调用上方独立判定。
        metrics = shading_metrics(run.rgb)
        ok, reason = check(metrics, run.limits, run.expected_size)
        # 3. 记录实测值和判定，失败时在本脚本显式抛出异常。
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
