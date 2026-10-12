"""CAM-SHP-011：斜边 SFR 整体清晰度
测试大类：清晰度 / SFR。
场景：打印版 3x3 斜边图卡（左上/上中/右上/左中/中心/右中/左下/下中/右下共 9 个黑白斜边方块）的整幅实拍图。
判定：定位图卡并矫正 -> 必须锁定全部 9 个斜边方块，否则立即失败且不计算 SFR ->
      在原图像素上做斜边 SFR；有效斜边数量、图卡置信度和整体 MTF50 中位数均达标才通过。
图片来源：专项 plan 的 --picture 提供真实拍摄图。
阈值来源：CASE_LIMITS；MTF50 下限 0.3 cycles/pixel 由需求方指定，仍需 Golden/Bad 样本复核。
重要限制：未做 OECF 线性化，不是 ISO 12233 eSFR 认证；单位为原图 cycles/pixel。
"""

import os

from autotest_runner import autotest

from autotest_runner.camera.execution import camera_case
from autotest_runner.camera.metrics import annotate_chart_quad, save_rgb_image
from autotest_runner.camera.sfr import (
    annotate_sfr_targets,
    find_chart_and_targets,
    measure_chart_sfr,
    plot_sfr_curves,
    plot_sfr_esf,
    save_sfr_edge_crops,
)


CASE_LIMITS = {
    # 9 个斜边方块必须全部锁定；其中至少 7 条斜边可算。
    "min_valid_targets": 9,
    "min_valid_edges": 7,
    "chart_confidence_min": 0.35,
    # 需求方指定的 MTF50 下限（cycles/pixel，原图像素）。
    "mtf50_min_cy_px": 0.3,
}

try:
    CASE_LIMITS["mtf50_min_cy_px"] = float(
        os.getenv("SFR_EDGE_MTF50_MIN_CY_PX", CASE_LIMITS["mtf50_min_cy_px"])
    )
except (TypeError, ValueError) as exc:
    raise ValueError("SFR_EDGE_MTF50_MIN_CY_PX 必须是 cycles/pixel 数值") from exc

METRIC_KEYS = (
    "sfr_configured_target_count",
    "sfr_valid_target_count",
    "sfr_targets_with_valid_edge_count",
    "sfr_configured_edge_count",
    "sfr_valid_edge_count",
    "sfr_mtf50_cy_px",
    "sfr_mtf20_cy_px",
    "sfr_mtf50_lw_ph",
    "sfr_mtf50_min_cy_px",
    "sfr_mtf50_max_cy_px",
    "sfr_mtf50_cv",
    "sfr_mtf50_by_group",
    "sfr_mtf50_by_target",
    "sfr_mtf50_horizontal_cy_px",
    "sfr_mtf50_vertical_cy_px",
    "sfr_corner_center_ratio",
    "sfr_unit",
    "sfr_chart_attempts",
    "sfr_chart_detection_image",
    "sfr_chart_rectified_image",
    "sfr_target_annotation_image",
    "sfr_edge_crop_images",
    "sfr_curve_plot_image",
    "sfr_esf_plot_image",
)


def check(metrics, limits, expected_size):
    """判定测量是否有效，并用整体 MTF50 中位数与下限比较。"""
    targets = metrics["sfr_valid_target_count"]
    edges = metrics["sfr_valid_edge_count"]
    confidence = float(metrics.get("sfr_chart_detection", {}).get("confidence", 0.0))
    mtf50 = metrics["sfr_mtf50_cy_px"]
    mtf20 = metrics["sfr_mtf20_cy_px"]
    lw_ph = metrics["sfr_mtf50_lw_ph"]
    measurable = (
        targets >= limits["min_valid_targets"]
        and edges >= limits["min_valid_edges"]
        and confidence >= limits["chart_confidence_min"]
        and mtf50 is not None
    )
    ok = measurable and mtf50 >= limits["mtf50_min_cy_px"]
    mtf20_text = f"{mtf20:.4f}" if mtf20 is not None else "N/A"
    if not measurable:
        mtf50_text = f"{mtf50:.4f}" if mtf50 is not None else "N/A"
        return False, (
            f"FAIL: SFR 测量无效；chart_confidence={confidence:.3f}; "
            f"locked_targets={targets}/{metrics['sfr_configured_target_count']}(需≥{limits['min_valid_targets']}); "
            f"targets_with_valid_edges={metrics.get('sfr_targets_with_valid_edge_count', 0)}; "
            f"valid_edges={edges}/{metrics['sfr_configured_edge_count']}(需≥{limits['min_valid_edges']}); "
            f"MTF50={mtf50_text}；请检查构图、对焦和 sfr_edges 中的错误原因"
        )
    status = "PASS" if ok else "FAIL"
    suffix = "" if ok else f"; required MTF50 >= {limits['mtf50_min_cy_px']:.4f} cycles/pixel"
    return ok, (
        f"{status}: chart_confidence={confidence:.3f}; locked_targets={targets}; "
        f"targets_with_valid_edges={metrics.get('sfr_targets_with_valid_edge_count', 0)}; valid_edges={edges}; "
        f"median MTF50={mtf50:.4f} cycles/pixel ({lw_ph:.0f} LW/PH); MTF20={mtf20_text} cycles/pixel; "
        f"limit={limits['mtf50_min_cy_px']:.4f} cycles/pixel{suffix}"
    )


@autotest(
    case_id="CAM-SHP-011",
    title="CAM-SHP-011 斜边 SFR 整体清晰度",
    priority="P1",
    test_class="清晰度 / Sharpness",
    description=(
        "对整幅实拍的 3x3 斜边图卡先定位矫正，再锁定 9 个黑白斜边方块，"
        "在原图像素上做斜边法 SFR，输出整体 MTF50/MTF20、各位置、各分组和角/中心比。"
    ),
    expected_result=(
        "至少 7 条斜边得到有效 MTF50，整体 MTF50 中位数不低于 0.3 cycles/pixel；"
        "图卡或 9 个斜边方块任一未锁定时立即失败且不计算 SFR；"
        "ESF/SFR 曲线、斜边锁定图和每个目标的原图裁剪全部保存。"
    ),
    parameters=CASE_LIMITS,
)
def test_sharpness_slanted_edge_sfr(request, record_property):
    """按五步流程执行斜边 SFR。"""
    with camera_case(request, record_property, CASE_LIMITS) as run:
        chart, located, attempts = find_chart_and_targets(run.rgb)
        metrics = {
            "sfr_chart_detection": {k: v for k, v in chart.items() if k != "rgb"},
            "sfr_chart_attempts": attempts,
        }
        if not chart.get("valid"):
            raise ValueError(f"未能定位图卡平面，已停止，不计算 SFR；检测结果={metrics['sfr_chart_detection']}")
        stem = run.artifact.stem
        folder = run.artifact.parent
        metrics["sfr_chart_detection_image"] = annotate_chart_quad(
            run.rgb, chart, run.artifact.with_name(f"{stem}_chart_detected.jpg")
        )
        metrics["sfr_chart_rectified_image"] = save_rgb_image(
            chart["rgb"], run.artifact.with_name(f"{stem}_chart_rectified.png")
        )
        missing = [item for item in located if not item["valid"]]
        if missing:
            # 识别错或识别不全时只保留诊断证据，不做任何 SFR 计算。
            metrics["sfr_targets"] = located
            metrics["sfr_edges"] = []
            metrics["sfr_target_annotation_image"] = annotate_sfr_targets(
                chart["rgb"], metrics, run.artifact.with_name(f"{stem}_targets.png")
            )
            reason = (
                f"FAIL: 图卡目标锁定失败({len(located) - len(missing)}/{len(located)})，已停止，不计算 SFR；"
                + "；".join(f"{item['name']}: {item['error']}" for item in missing)
            )
            run.record(metrics, False, reason, METRIC_KEYS)
            raise AssertionError(f"{run.case_id}: {reason}")
        metrics.update(measure_chart_sfr(run.rgb, chart, located))
        metrics["sfr_target_annotation_image"] = annotate_sfr_targets(
            chart["rgb"], metrics, run.artifact.with_name(f"{stem}_targets.png")
        )
        metrics["sfr_edge_crop_images"] = save_sfr_edge_crops(run.rgb, metrics, folder, stem)
        metrics["sfr_curve_plot_image"] = plot_sfr_curves(
            metrics, run.artifact.with_name(f"{stem}_sfr.png")
        )
        metrics["sfr_esf_plot_image"] = plot_sfr_esf(
            metrics, run.artifact.with_name(f"{stem}_esf.png")
        )
        ok, reason = check(metrics, run.limits, run.expected_size)
        run.record(metrics, ok, reason, METRIC_KEYS)
        if not ok:
            raise AssertionError(f"{run.case_id}: {reason}")
