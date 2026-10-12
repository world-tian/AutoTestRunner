"""CAM-SHP-010：旧式 ISO/CIPA 图卡西门子星 MTF 试验
测试大类：清晰度 / MTF。
目的：从手机或设备拍摄的西门子星区域估计 MTF50/MTF20。
输入来源：实拍图由专项 plan 的 --picture 提供；先定位图卡平面并透视矫正，再按图卡归一化坐标取 ROI。
判定标准：6 颗星（中间 2 颗 + 四角 4 颗）都必须可计算出 MTF50；MTF20 作为可选辅助值输出；产品下限需用 Golden/Bad 样本另行标定。
重要限制：该图是旧式高反差视觉分辨率图，不是 ISO 12233:2014/2023 eSFR 标准靶，
           本用例统一输出 cycles/pixel，只作可复现实验测量。
"""

import json
import os
import re

from autotest_runner import autotest

from autotest_runner.camera.advanced import evaluate
from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import (
    annotate_chart_quad,
    annotate_siemens_star_metrics,
    plot_siemens_star_mtf,
    rectify_chart,
    save_rgb_image,
    save_siemens_star_crops,
)


CASE_LIMITS = {
    # 这是“测量链路有效”门槛，不是产品 MTF 性能下限；后续以 Golden/Bad 标定替换。
    "min_valid_stars": 6,
    "chart_confidence_min": 0.35,
    # Provisional separation for the two current real samples: pic1 is about
    # pic1 is about 0.358 cycles/pixel and pic2 about 0.246 cycles/pixel after
    # center refinement. Replace
    # with Golden/Bad calibration data before treating this as a product limit.
    "mtf50_min_cy_px": 0.300,
}

try:
    CASE_LIMITS["mtf50_min_cy_px"] = float(
        os.getenv("SFR_MTF50_MIN_CY_PX", CASE_LIMITS["mtf50_min_cy_px"])
    )
except (TypeError, ValueError) as exc:
    raise ValueError("SFR_MTF50_MIN_CY_PX 必须是 cycles/pixel 数值") from exc

METRIC_KEYS = (
    "siemens_star_configured_count",
    "siemens_star_valid_count",
    "siemens_star_mtf50_by_region",
    "siemens_star_mtf20_by_region",
    "siemens_star_mtf50_cy_px",
    "siemens_star_mtf20_cy_px",
    "siemens_star_mtf_unit",
    "siemens_star_regions",
    "siemens_chart_detection",
    "siemens_chart_detection_image",
    "siemens_chart_rectified_image",
    "siemens_star_roi_image",
    "siemens_star_crop_images",
    "siemens_star_mtf_plot_image",
)


def check(metrics, limits, expected_size):
    """只判定 ROI 是否有效并输出 MTF，不把示意图结果当产品阈值。"""
    valid_count = metrics["siemens_star_valid_count"]
    chart_confidence = float(metrics.get("siemens_chart_detection", {}).get("confidence", 0.0))
    mtf50 = metrics["siemens_star_mtf50_cy_px"]
    mtf20 = metrics["siemens_star_mtf20_cy_px"]
    ok = (
        valid_count >= limits["min_valid_stars"]
        and chart_confidence >= limits["chart_confidence_min"]
        and mtf50 is not None
        and mtf50 >= limits["mtf50_min_cy_px"]
    )
    if ok:
        reason = (
            f"有效西门子星={valid_count}；MTF50={mtf50:.6f} cycles/pixel，"
            f"MTF20={mtf20:.6f} cycles/pixel；产品阈值待标定"
            if mtf20 is not None else
            f"有效西门子星={valid_count}；MTF50={mtf50:.6f} cycles/pixel，MTF20=N/A；产品阈值待标定"
        )
    else:
        reason = (
            f"西门子星 MTF 测量无效：有效星={valid_count}，"
            f"MTF50={mtf50}，MTF20={mtf20}；请检查 ROI、周期数和实拍构图"
        )
    reason = (
        f"PASS: chart_confidence={chart_confidence:.3f}; valid_stars={valid_count}; MTF50={mtf50:.4f} cycles/pixel; "
        f"MTF20={mtf20:.4f} cycles/pixel; limit={limits['mtf50_min_cy_px']:.3f} cycles/pixel"
        if ok and mtf20 is not None else
        f"PASS: chart_confidence={chart_confidence:.3f}; valid_stars={valid_count}; MTF50={mtf50:.4f} cycles/pixel; "
        f"MTF20=N/A; limit={limits['mtf50_min_cy_px']:.3f} cycles/pixel"
        if ok else
        f"FAIL: chart_confidence={chart_confidence:.3f}; valid_stars={valid_count}; MTF50={mtf50} cycles/pixel; "
        f"MTF20={mtf20} cycles/pixel; required MTF50 >= {limits['mtf50_min_cy_px']:.3f} cycles/pixel"
    )
    return ok, reason


def parse_regions(raw_regions):
    """解析 JSON；兼容 PowerShell 原生参数传递去掉内部双引号的形式。"""
    try:
        return json.loads(raw_regions)
    except json.JSONDecodeError as original_error:
        # PowerShell 将 JSON 直接作为原生进程参数传递时，可能变成
        # [{name:left_mid,x:0.35,y:0.39,radius:0.05,cycles:36}]。
        relaxed = re.sub(r"([\[{,]\s*)([A-Za-z_][\w-]*)(\s*:)", r'\1"\2"\3', raw_regions)
        relaxed = re.sub(r"(:\s*)([A-Za-z_][\w-]*)(\s*[,}])", r'\1"\2"\3', relaxed)
        # Some Windows shells drop a closing brace at the end of a quoted
        # argument. Restore only the objectively unbalanced braces.
        if relaxed.endswith("]") and relaxed.count("{") > relaxed.count("}"):
            missing = relaxed.count("{") - relaxed.count("}")
            relaxed = relaxed[:-1] + ("}" * missing) + "]"
        try:
            return json.loads(relaxed)
        except json.JSONDecodeError:
            raise ValueError("SFR_STAR_REGIONS 必须是 JSON 数组") from original_error


@autotest(
    case_id="CAM-SHP-010",
    title="CAM-SHP-010 西门子星 MTF50/MTF20 试验",
    priority="P1",
    test_class="清晰度 / Sharpness",
    description=(
        "对旧式 ISO/CIPA 高反差图卡中的西门子星做径向调制度测量，输出 MTF50/MTF20。"
        "需要真实拍摄图和图卡平面坐标；结果不是 ISO 12233 eSFR 正式认证值。"
    ),
    expected_result=(
        "6 颗已配置西门子星（中间 2 颗 + 四角 4 颗）都得到有效 MTF50，单位为 cycles/pixel；"
        "同时尽量输出 MTF20 辅助值；"
        "产品性能阈值须由固定图卡、距离、光照和 Golden/Bad 样本标定。"
    ),
    parameters=CASE_LIMITS,
)
def test_sharpness_siemens_star_mtf(request, record_property):
    """按五步流程执行西门子星 MTF 试验。"""
    with camera_case(request, record_property, CASE_LIMITS) as run:
        raw_regions = os.getenv("SFR_STAR_REGIONS", "")
        print(f"[CAMERA] {run.case_id} ROI config: {raw_regions!r}", flush=True)
        if not raw_regions:
            raise ValueError(
                "未设置 SFR_STAR_REGIONS；请先标注星位置，例如 "
                "[{\"name\":\"center\",\"x\":0.50,\"y\":0.50,\"radius\":0.20,\"cycles\":18}]"
            )
        regions = parse_regions(raw_regions)
        chart = rectify_chart(run.rgb, canonical_size=(1800, 1000))
        metrics = {
            "siemens_chart_detection": {
                key: value for key, value in chart.items() if key != "rgb"
            }
        }
        if not chart.get("valid"):
            raise ValueError(
                "未能定位图卡四角/亮色图卡平面，已拒绝使用整图固定坐标；"
                f"检测结果={json.dumps(metrics['siemens_chart_detection'], ensure_ascii=False)}"
            )
        chart_detection_path = run.artifact.with_name(f"{run.artifact.stem}_chart_detected.jpg")
        metrics["siemens_chart_detection_image"] = annotate_chart_quad(
            run.rgb, chart, chart_detection_path
        )

        # The plan coordinates are normalized to the rectified chart plane,
        # so camera distance, tilt and moderate perspective no longer move an
        # ROI onto a neighboring pattern.
        run.rgb = chart["rgb"]
        metrics.update(evaluate("siemens_star", run, regions))
        rectified_path = run.artifact.with_name(f"{run.artifact.stem}_chart_rectified.png")
        metrics["siemens_chart_rectified_image"] = save_rgb_image(run.rgb, rectified_path)

        annotation_path = run.artifact.with_name(f"{run.artifact.stem}_roi.png")
        metrics["siemens_star_roi_image"] = annotate_siemens_star_metrics(
            run.rgb, metrics, annotation_path
        )
        metrics["siemens_star_crop_images"] = save_siemens_star_crops(
            run.rgb, metrics, run.artifact.parent, run.artifact.stem
        )
        plot_path = run.artifact.with_name(f"{run.artifact.stem}_mtf.png")
        metrics["siemens_star_mtf_plot_image"] = plot_siemens_star_mtf(metrics, plot_path)
        ok, reason = check(metrics, run.limits, run.expected_size)
        run.record(metrics, ok, reason, METRIC_KEYS)
        if ok is False:
            raise AssertionError(f"{run.case_id}: {reason}")
