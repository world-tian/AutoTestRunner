"""斜边 SFR（MTF）筛查：图卡斜边锁定、ESF/LSF/SFR 计算和过程证据图。

流程：图卡透视矫正 -> 在矫正平面按形状锁定倾斜方块/条 -> 逆变换回原图像素 ->
在原图像素上逐条边做斜边法（亚像素直线拟合、4 倍过采样 ESF、LSF、Hamming 窗、FFT）。
频率单位为 cycles/pixel（原图像素）。这是 ISO 12233 斜边法思路的筛查实现，
没有 OECF 线性化，也不使用标准 eSFR 靶，不能当作认证值。
"""

import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .metrics import _mtf_crossing, detect_chart_quad, luminance, rectify_chart

CANONICAL_SIZE = (1500, 1000)
OVERSAMPLE = 4
NYQUIST_CY_PX = 0.5
MIN_EDGE_LENGTH_PX = 60.0
MIN_EDGE_ANGLE_DEG = 1.0
MAX_EDGE_ANGLE_DEG = 20.0
MIN_EDGE_CONTRAST = 20.0
MIN_ESF_ROWS = 40

# 3x3 斜边图卡：每个方块左白右黑，白黑交界是一条 5°–12° 的斜边。
# center/size 为矫正平面(1500x1000)内“黑色部分”的期望中心和(宽, 高)像素。
# 不同照片的矫正平面范围会有数十像素差异，所以只按形状（面积、位置、斜边倾角）在
# center±(长边/2+tolerance) 的窗口内挑选；精确边由亚像素拟合得到。
_COLUMNS = (290, 802, 1328)
_ROWS = (177, 469, 756)
_NAMES = (("tl", "tm", "tr"), ("ml", "mc", "mr"), ("bl", "bm", "br"))
_GROUPS = {"tl": "corner", "tr": "corner", "bl": "corner", "br": "corner",
           "tm": "edge_mid", "ml": "edge_mid", "mr": "edge_mid", "bm": "edge_mid", "mc": "center"}
CHART_TARGETS = tuple(
    {"name": f"patch_{_NAMES[row][column]}", "group": _GROUPS[_NAMES[row][column]],
     "center": (_COLUMNS[column], _ROWS[row]), "size": (132, 196), "tolerance": 70}
    for row in range(3) for column in range(3)
)

GROUP_COLORS = {
    "corner": (30, 105, 190),
    "edge_mid": (215, 85, 45),
    "center": (35, 145, 85),
}


def _target_window(target, shape):
    cx, cy = target["center"]
    half = max(target["size"]) / 2.0 + target["tolerance"]
    height, width = shape[:2]
    return (int(max(0, cx - half)), int(max(0, cy - half)),
            int(min(width, cx + half)), int(min(height, cy + half)))


def _slanted_edge_index(polygon, min_length):
    """在四边形中找最长的近竖直斜边，返回起点序号；没有则返回 None。"""
    best = None
    for index in range(len(polygon)):
        delta = polygon[(index + 1) % len(polygon)] - polygon[index]
        length = float(np.hypot(*delta))
        angle = math.degrees(math.atan2(abs(delta[0]), abs(delta[1])))
        if 2.0 <= angle <= 25.0 and length >= min_length and (best is None or length > best[0]):
            best = (length, index)
    return None if best is None else best[1]


def locate_target(gray_u8, target):
    """锁定一个"左白右黑"斜边方块的黑色部分，返回其四角和斜边序号（矫正平面像素）。"""
    x0, y0, x1, y1 = _target_window(target, gray_u8.shape)
    result = {"name": target["name"], "group": target["group"], "window": [x0, y0, x1, y1]}
    crop = gray_u8[y0:y1, x0:x1]
    if crop.size == 0:
        return {**result, "valid": False, "error": "窗口超出图卡平面"}
    blur = cv2.GaussianBlur(crop, (0, 0), 1.5)
    threshold, _ = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = (blur < threshold).astype(np.uint8) * 255
    # 开运算去掉方块外框细线和下方文字，只保留黑色大块。
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    expected_width, expected_height = target["size"]
    expected_area = 0.95 * expected_width * expected_height
    expected_center = np.array(target["center"], dtype=np.float64) - [x0, y0]
    rejected, candidates = [], []
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < 0.3 * expected_area:
            continue
        moments = cv2.moments(contour)
        centroid = np.array([moments["m10"] / moments["m00"], moments["m01"] / moments["m00"]])
        bx, by, bw, bh = cv2.boundingRect(contour)
        if bx <= 1 or by <= 1 or bx + bw >= crop.shape[1] - 1 or by + bh >= crop.shape[0] - 1:
            rejected.append("与窗口边界相连")
        elif not 0.55 * expected_area <= area <= 1.45 * expected_area:
            rejected.append(f"面积{area:.0f}不符(期望≈{expected_area:.0f})")
        elif np.linalg.norm(centroid - expected_center) > target["tolerance"] + 0.5 * expected_width:
            rejected.append("位置偏离期望过远")
        else:
            candidates.append((float(np.linalg.norm(centroid - expected_center)), area, contour))
    if not candidates:
        reason = "；".join(rejected[:3]) if rejected else "窗口内没有黑色方块"
        return {**result, "valid": False, "threshold": float(threshold), "error": f"未锁定到目标：{reason}"}
    _, area, contour = min(candidates, key=lambda item: item[0])
    hull = cv2.convexHull(contour)
    perimeter = cv2.arcLength(hull, True)
    polygon = None
    for fraction in (0.02, 0.03, 0.05, 0.08):
        approx = cv2.approxPolyDP(hull, fraction * perimeter, True).reshape(-1, 2).astype(np.float64)
        if len(approx) == 4:
            polygon = approx
            break
    if polygon is None:
        return {**result, "valid": False, "threshold": float(threshold), "error": "黑色块不是四边形，无法确定斜边"}
    edge_index = _slanted_edge_index(polygon, 0.6 * expected_height)
    if edge_index is None:
        return {**result, "valid": False, "threshold": float(threshold),
                "error": "黑色块中没有长度和倾角合适的斜边（可能不是斜边方块）"}
    polygon = polygon + np.array([x0, y0], dtype=np.float64)
    return {
        **result,
        "valid": True,
        "polygon_canonical": polygon.round(2).tolist(),
        "edge_index": int(edge_index),
        "center_canonical": polygon.mean(axis=0).round(2).tolist(),
        "area_canonical": area,
        "threshold": float(threshold),
    }


def _side_name(canon_a, canon_b, center):
    direction = canon_b - canon_a
    middle = (canon_a + canon_b) / 2.0 - center
    if abs(direction[0]) < abs(direction[1]):
        return "left" if middle[0] < 0 else "right"
    return "top" if middle[1] < 0 else "bottom"


def build_edges(located, inverse_matrix):
    """把锁定目标的斜边映射回原图像素。"""
    edges = []
    for item in located:
        if not item.get("valid"):
            continue
        canonical = np.asarray(item["polygon_canonical"], dtype=np.float64)
        original = cv2.perspectiveTransform(
            canonical.reshape(-1, 1, 2), inverse_matrix
        ).reshape(-1, 2)
        center = canonical.mean(axis=0)
        index = item["edge_index"]
        nxt = (index + 1) % len(canonical)
        edges.append({
            "name": f"{item['name']}_{_side_name(canonical[index], canonical[nxt], center)}",
            "target": item["name"],
            "group": item["group"],
            "p0": original[index],
            "p1": original[nxt],
            "canonical": [canonical[index].tolist(), canonical[nxt].tolist()],
            "length_px": float(np.linalg.norm(original[nxt] - original[index])),
        })
    return edges


def _robust_line(rows, centers):
    """x = slope*y + intercept，迭代剔除离群行。"""
    keep = np.ones(len(rows), dtype=bool)
    slope, intercept = np.polyfit(rows, centers, 1)
    for _ in range(3):
        residual = centers - (slope * rows + intercept)
        mad = float(np.median(np.abs(residual[keep] - np.median(residual[keep]))))
        limit = max(0.5, 3.0 * 1.4826 * mad)
        keep = np.abs(residual) <= limit
        if keep.sum() < 10:
            break
        slope, intercept = np.polyfit(rows[keep], centers[keep], 1)
    residual = centers[keep] - (slope * rows[keep] + intercept)
    return float(slope), float(intercept), float(np.sqrt(np.mean(residual ** 2))), int(keep.sum())


def measure_edge(rgb, p0, p1, half_width, trim=0.15):
    """对一条近似直边做斜边 SFR；坐标为原图像素 (x, y)。"""
    p0 = np.asarray(p0, dtype=np.float64)
    p1 = np.asarray(p1, dtype=np.float64)
    pad = int(half_width) + 6
    height, width = rgb.shape[:2]
    x_min = int(max(0, math.floor(min(p0[0], p1[0]) - pad)))
    x_max = int(min(width, math.ceil(max(p0[0], p1[0]) + pad) + 1))
    y_min = int(max(0, math.floor(min(p0[1], p1[1]) - pad)))
    y_max = int(min(height, math.ceil(max(p0[1], p1[1]) + pad) + 1))
    if x_max - x_min < 8 or y_max - y_min < 8:
        return {"valid": False, "error": "边缘超出图像范围"}
    gray = luminance(rgb[y_min:y_max, x_min:x_max])
    q0 = p0 - [x_min, y_min]
    q1 = p1 - [x_min, y_min]
    vertical_edge = abs(q1[1] - q0[1]) >= abs(q1[0] - q0[0])
    if not vertical_edge:
        gray = gray.T
        q0, q1 = q0[::-1], q1[::-1]
    if q0[1] > q1[1]:
        q0, q1 = q1, q0
    rows_total, cols_total = gray.shape
    y_a = q0[1] + trim * (q1[1] - q0[1])
    y_b = q1[1] - trim * (q1[1] - q0[1])
    rows = np.arange(int(math.ceil(y_a)), int(math.floor(y_b)) + 1)
    rows = rows[(rows >= 0) & (rows < rows_total)]
    if len(rows) < MIN_ESF_ROWS:
        return {"valid": False, "error": f"可用扫描行不足({len(rows)}<{MIN_ESF_ROWS})"}
    slope = (q1[0] - q0[0]) / (q1[1] - q0[1])
    intercept = q0[0] - slope * q0[1]
    half = int(half_width)
    offsets = np.arange(-half, half + 1)
    window = np.hanning(2 * half + 2)[1:-1]  # 与 np.diff 后的 2*half 个点等长

    centers = rows_used = None
    for _ in range(4):
        edge_x = np.round(slope * rows + intercept).astype(int)
        columns = edge_x[:, None] + offsets[None, :]
        ok = (columns.min(axis=1) >= 0) & (columns.max(axis=1) < cols_total)
        if ok.sum() < MIN_ESF_ROWS:
            return {"valid": False, "error": "边缘带超出图像范围"}
        profile = gray[rows[ok][:, None], columns[ok]]
        derivative = np.diff(profile, axis=1) * window[None, :]
        total = derivative.sum(axis=1)
        sign = np.sign(np.median(total))
        good = (np.abs(total) >= 5.0) & (np.sign(total) == sign)
        if good.sum() < MIN_ESF_ROWS:
            return {"valid": False, "error": "边缘对比度不足，无法逐行定位边缘"}
        positions = np.arange(derivative.shape[1])[None, :]
        centroid = (positions * derivative).sum(axis=1) / np.where(total == 0, 1, total)
        centers = columns[ok][:, 0] + 0.5 + centroid
        rows_used = rows[ok]
        slope, intercept, line_rms, fit_count = _robust_line(
            rows_used[good].astype(float), centers[good]
        )
    angle = math.degrees(math.atan(abs(slope)))
    fit_rows = (float(rows_used[0]), float(rows_used[-1]))
    fitted_oriented = [
        np.array([slope * row + intercept, row], dtype=np.float64)
        for row in fit_rows
    ]
    if vertical_edge:
        fitted_global = [point + [x_min, y_min] for point in fitted_oriented]
    else:
        fitted_global = [
            np.array([x_min + point[1], y_min + point[0]], dtype=np.float64)
            for point in fitted_oriented
        ]
    base = {
        "edge_orientation": "vertical" if vertical_edge else "horizontal",
        "sfr_direction": "horizontal" if vertical_edge else "vertical",
        "edge_angle_deg": float(angle),
        "line_rms_px": float(line_rms),
        "rows_used": int(fit_count),
        "half_width_px": half,
        "fitted_edge_p0_px": fitted_global[0].round(4).tolist(),
        "fitted_edge_p1_px": fitted_global[1].round(4).tolist(),
    }
    if line_rms > 1.5:
        return {**base, "valid": False, "error": f"边缘拟合残差过大({line_rms:.2f}px)，边不够直或定位错误"}
    if not MIN_EDGE_ANGLE_DEG <= angle <= MAX_EDGE_ANGLE_DEG:
        return {**base, "valid": False,
                "error": f"边缘倾角{angle:.2f}°不在{MIN_EDGE_ANGLE_DEG}-{MAX_EDGE_ANGLE_DEG}°，不适合斜边法"}

    cos_theta = 1.0 / math.sqrt(1.0 + slope ** 2)
    edge_x = np.round(slope * rows + intercept).astype(int)
    columns = edge_x[:, None] + np.arange(-half - 2, half + 3)[None, :]
    ok = (columns.min(axis=1) >= 0) & (columns.max(axis=1) < cols_total)
    rows_e = rows[ok]
    columns = columns[ok]
    values = gray[rows_e[:, None], columns]
    distance = (columns - (slope * rows_e[:, None] + intercept)) * cos_theta
    inside = np.abs(distance) <= half * cos_theta
    bins = int(math.floor(2 * half * cos_theta * OVERSAMPLE)) + 1
    index = np.floor((distance[inside] + half * cos_theta) * OVERSAMPLE).astype(int)
    index = np.clip(index, 0, bins - 1)
    sums = np.bincount(index, weights=values[inside], minlength=bins)
    counts = np.bincount(index, minlength=bins)
    filled = counts > 0
    empty_fraction = 1.0 - float(filled.mean())
    if empty_fraction > 0.10:
        return {**base, "valid": False, "empty_bin_fraction": empty_fraction,
                "error": f"ESF 过采样空箱比例过高({empty_fraction:.2f})，边缘倾角或行数不足"}
    axis = (np.arange(bins) + 0.5) / OVERSAMPLE - half * cos_theta
    esf = np.interp(np.arange(bins), np.flatnonzero(filled), sums[filled] / counts[filled])
    edge_count = max(3, int(bins * 0.15))
    low, high = float(np.median(esf[:edge_count])), float(np.median(esf[-edge_count:]))
    contrast = abs(high - low)
    base.update(contrast=float(contrast), empty_bin_fraction=empty_fraction)
    if contrast < MIN_EDGE_CONTRAST:
        return {**base, "valid": False, "error": f"边缘对比度过低({contrast:.1f}<{MIN_EDGE_CONTRAST})"}
    if high < low:
        esf = -esf
    normalized = (esf - esf[:edge_count].mean()) / max(
        esf[-edge_count:].mean() - esf[:edge_count].mean(), 1e-9
    )
    lsf = np.gradient(esf, 1.0 / OVERSAMPLE)
    smooth = np.convolve(np.abs(lsf), np.ones(5) / 5.0, mode="same")
    peak = int(np.argmax(smooth))
    positions = np.arange(len(lsf))
    taper = np.where(np.abs(positions - peak) <= len(lsf) / 2.0,
                     0.54 + 0.46 * np.cos(2 * np.pi * (positions - peak) / len(lsf)), 0.0)
    windowed = lsf * taper
    nfft = 8192
    spectrum = np.abs(np.fft.rfft(windowed, n=nfft))
    frequency = np.fft.rfftfreq(nfft, d=1.0 / OVERSAMPLE)
    if spectrum[0] <= 1e-9:
        return {**base, "valid": False, "error": "LSF 能量无效"}
    sfr = spectrum / spectrum[0]
    keep = frequency <= 1.0
    frequency, sfr = frequency[keep], sfr[keep] / np.sinc(2.0 * frequency[keep] / OVERSAMPLE)
    crossing50 = _mtf_crossing(frequency, sfr, 0.5)
    crossing20 = _mtf_crossing(frequency, sfr, 0.2)
    rise_low = _first_crossing(axis, normalized, 0.1)
    rise_high = _first_crossing(axis, normalized, 0.9)
    rise = float(rise_high - rise_low) if rise_low is not None and rise_high is not None else None
    if rise is not None and rise > 0.9 * half * cos_theta:
        return {**base, "valid": False, "rise_10_90_px": rise,
                "error": f"边缘过渡({rise:.1f}px)超过取样带宽，请检查对焦或距离"}
    stride = 8
    return {
        **base,
        "valid": True,
        "rise_10_90_px": rise,
        "mtf50_crossing_cy_px": crossing50,
        "mtf20_crossing_cy_px": crossing20,
        "mtf50_cy_px": crossing50 if crossing50 is not None and crossing50 <= NYQUIST_CY_PX else None,
        "mtf20_cy_px": crossing20 if crossing20 is not None and crossing20 <= NYQUIST_CY_PX else None,
        "mtf_at_0p25_cy_px": float(np.interp(0.25, frequency, sfr)),
        "sfr_curve": [
            {"frequency_cy_px": round(float(f), 5), "mtf": round(float(m), 5)}
            for f, m in zip(frequency[::stride], sfr[::stride])
        ],
        "esf_curve": [
            {"distance_px": round(float(d), 4), "value": round(float(v), 5)}
            for d, v in zip(axis, normalized)
        ],
        "esf_low_level": low,
        "esf_high_level": high,
    }


def _first_crossing(axis, values, level):
    for index in range(1, len(values)):
        if values[index - 1] < level <= values[index]:
            span = values[index] - values[index - 1]
            fraction = 0.0 if span == 0 else (level - values[index - 1]) / span
            return float(axis[index - 1] + fraction * (axis[index] - axis[index - 1]))
    return None


def _median(values):
    values = [value for value in values if value is not None]
    return float(np.median(values)) if values else None


def _chart_from_target_lattice(rgb, targets=CHART_TARGETS):
    """Use the nine black slanted-edge patches themselves to recover chart perspective."""
    if len(targets) != 9:
        return None
    image = np.asarray(np.clip(rgb, 0, 255), dtype=np.uint8)
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    height, width = gray.shape
    image_area = float(width * height)
    expected = np.asarray([target["center"] for target in targets], dtype=np.float32)
    best = None
    for threshold in (20, 28, 36, 44, 52, 60):
        mask = (gray < threshold).astype(np.uint8) * 255
        count, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
        components = []
        for index in range(1, count):
            x, y, box_width, box_height, area = stats[index]
            aspect = box_width / max(box_height, 1)
            fraction = area / image_area
            if (0.003 <= fraction <= 0.035
                    and 0.42 <= aspect <= 1.08
                    and box_width >= width * 0.025
                    and box_height >= height * 0.07):
                components.append({
                    "center": centroids[index].astype(np.float32),
                    "area": int(area),
                    "bbox": [int(x), int(y), int(box_width), int(box_height)],
                })
        if len(components) < 9:
            continue

        # Select nine large black components, then group their centers into three rows.
        components = sorted(components, key=lambda item: item["area"], reverse=True)[:18]
        components.sort(key=lambda item: float(item["center"][1]))
        row_groups = []
        row_tolerance = height * 0.075
        for component in components:
            if not row_groups or abs(float(component["center"][1]) - np.median(
                    [item["center"][1] for item in row_groups[-1]])) > row_tolerance:
                row_groups.append([component])
            else:
                row_groups[-1].append(component)
        if len(row_groups) != 3 or any(len(row) < 3 for row in row_groups):
            continue
        rows = [sorted(row, key=lambda item: float(item["center"][0]))[:3] for row in row_groups]
        observed = np.asarray([item["center"] for row in rows for item in row], dtype=np.float32)
        matrix, inliers = cv2.findHomography(expected, observed, cv2.RANSAC, max(12.0, min(width, height) * 0.01))
        if matrix is None or inliers is None or int(inliers.sum()) < 7:
            continue
        projected = cv2.perspectiveTransform(expected.reshape(1, -1, 2), matrix).reshape(-1, 2)
        residuals = np.linalg.norm(projected - observed, axis=1)
        inlier_mask = inliers.reshape(-1).astype(bool)
        rms = float(np.sqrt(np.mean(residuals[inlier_mask] ** 2)))
        if rms > max(12.0, min(width, height) * 0.012):
            continue
        corners_canonical = np.float32([[[0, 0], [CANONICAL_SIZE[0] - 1, 0],
                                          [CANONICAL_SIZE[0] - 1, CANONICAL_SIZE[1] - 1],
                                          [0, CANONICAL_SIZE[1] - 1]]])
        quad = cv2.perspectiveTransform(corners_canonical, matrix).reshape(-1, 2)
        if (np.any(quad[:, 0] < 0) or np.any(quad[:, 0] >= width)
                or np.any(quad[:, 1] < 0) or np.any(quad[:, 1] >= height)):
            continue
        score = float((int(inliers.sum()) / len(targets)) * np.exp(-rms / max(1.0, min(width, height) * 0.012)))
        if best is None or score > best[0]:
            best = (score, matrix, quad, rows, rms, threshold, residuals)

    if best is None:
        return None
    score, canonical_to_image, quad, rows, rms, threshold, residuals = best
    image_to_canonical = np.linalg.inv(canonical_to_image)
    chart_rgb = cv2.warpPerspective(
        image, image_to_canonical, CANONICAL_SIZE,
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
    )
    detection = {
        "valid": True,
        "method": "nine_target_lattice_homography",
        "confidence": score,
        "quad_image_px": quad.round(3).tolist(),
        "area_fraction": float(cv2.contourArea(quad.astype(np.float32)) / image_area),
        "aspect": float(np.linalg.norm(quad[1] - quad[0]) / max(np.linalg.norm(quad[3] - quad[0]), 1e-6)),
        "margin_px": int(max(0, min(quad[:, 0].min(), quad[:, 1].min(),
                                 width - quad[:, 0].max(), height - quad[:, 1].max()))),
        "threshold": float(threshold),
        "canonical_size": list(CANONICAL_SIZE),
        "quad_canonical_px": [[0.0, 0.0], [CANONICAL_SIZE[0] - 1.0, 0.0],
                              [CANONICAL_SIZE[0] - 1.0, CANONICAL_SIZE[1] - 1.0],
                              [0.0, CANONICAL_SIZE[1] - 1.0]],
        "perspective_transform": image_to_canonical.round(10).tolist(),
        "target_lattice_rms_px": rms,
        "target_lattice_centers_image_px": [item["center"].round(2).tolist() for row in rows for item in row],
        "target_lattice_residuals_px": residuals.round(3).tolist(),
    }
    return {**detection, "rgb": chart_rgb.astype(float)}


def find_chart_and_targets(rgb, targets=CHART_TARGETS):
    """在候选图卡平面中挑出能锁定全部目标的一个；锁定数量不足时返回得到目标最多的候选。

    最高分候选有时是整块屏幕/纸张，只有用图卡自身特征（目标形状）才能确认。
    返回 (chart, located, attempts)，chart 无效时 located 为空。
    """
    detection = detect_chart_quad(rgb)
    if not detection.get("valid"):
        detection = {**detection, "candidates": []}
    base = {key: value for key, value in detection.items() if key != "candidates"}
    best = None
    attempts = []
    for index, candidate in enumerate(detection["candidates"]):
        chart = rectify_chart(rgb, CANONICAL_SIZE, detection={**base, **candidate})
        gray = np.clip(luminance(chart["rgb"]), 0, 255).astype(np.uint8)
        located = [locate_target(gray, target) for target in targets]
        count = sum(1 for item in located if item["valid"])
        attempts.append({
            "candidate_index": index,
            "quad_image_px": candidate["quad_image_px"],
            "confidence": candidate["confidence"],
            "located_target_count": count,
            "configured_target_count": len(targets),
        })
        if best is None or count > best[0]:
            best = (count, chart, located)
        if count == len(targets):
            break
    if best is not None and best[0] == len(targets):
        return best[1], best[2], attempts

    lattice_chart = _chart_from_target_lattice(rgb, targets)
    if lattice_chart is not None:
        gray = np.clip(luminance(lattice_chart["rgb"]), 0, 255).astype(np.uint8)
        located = [locate_target(gray, target) for target in targets]
        count = sum(1 for item in located if item["valid"])
        attempts.append({
            "candidate_index": "target_lattice_fallback",
            "method": lattice_chart["method"],
            "quad_image_px": lattice_chart["quad_image_px"],
            "confidence": lattice_chart["confidence"],
            "target_lattice_rms_px": lattice_chart["target_lattice_rms_px"],
            "located_target_count": count,
            "configured_target_count": len(targets),
        })
        if count > (best[0] if best is not None else -1):
            return lattice_chart, located, attempts

    if best is not None:
        return best[1], best[2], attempts
    return {**detection, "valid": False, "rgb": np.asarray(rgb, dtype=float)}, [], attempts


def measure_chart_sfr(rgb, chart, located):
    """在原图像素上测量已锁定目标的所有可用斜边；chart 为 rectify_chart 的有效结果。"""
    inverse = np.linalg.inv(np.asarray(chart["perspective_transform"], dtype=np.float64))
    edges = build_edges(located, inverse)

    measured = []
    for edge in edges:
        entry = {
            "name": edge["name"], "target": edge["target"], "group": edge["group"],
            "p0_px": np.round(edge["p0"], 2).tolist(), "p1_px": np.round(edge["p1"], 2).tolist(),
            "canonical_segment": edge["canonical"], "length_px": edge["length_px"],
        }
        if edge["length_px"] < MIN_EDGE_LENGTH_PX:
            entry.update(valid=False, error=f"边长过短({edge['length_px']:.0f}px)")
        else:
            # 带宽需覆盖模糊过渡区；斜边两侧是整块黑/白，不会被对侧边限制。
            half = int(np.clip(0.3 * edge["length_px"], 16, 100))
            result = measure_edge(rgb, edge["p0"], edge["p1"], half)
            entry.update(result)
            if result.get("fitted_edge_p0_px") and result.get("fitted_edge_p1_px"):
                fitted_image_points = np.asarray(
                    [result["fitted_edge_p0_px"], result["fitted_edge_p1_px"]], dtype=np.float32
                ).reshape(-1, 1, 2)
                fitted_canonical = cv2.perspectiveTransform(
                    fitted_image_points,
                    np.asarray(chart["perspective_transform"], dtype=np.float64),
                ).reshape(-1, 2)
                entry["fitted_canonical_segment"] = fitted_canonical.round(4).tolist()
        measured.append(entry)

    valid = [edge for edge in measured if edge.get("valid")]
    by_target, by_group = {}, {}
    for edge in valid:
        by_target.setdefault(edge["target"], []).append(edge["mtf50_cy_px"])
        by_group.setdefault(edge["group"], []).append(edge["mtf50_cy_px"])
    mtf50_values = [edge["mtf50_cy_px"] for edge in valid if edge["mtf50_cy_px"] is not None]
    mean50 = float(np.mean(mtf50_values)) if mtf50_values else None
    group_median = {group: _median(values) for group, values in by_group.items()}
    center, corner = group_median.get("center"), group_median.get("corner")
    return {
        "sfr_targets": located,
        "sfr_edges": measured,
        "sfr_configured_target_count": len(located),
        "sfr_valid_target_count": sum(1 for target in located if target.get("valid")),
        "sfr_targets_with_valid_edge_count": len({edge["target"] for edge in valid}),
        "sfr_configured_edge_count": len(measured),
        "sfr_valid_edge_count": len(valid),
        "sfr_mtf50_cy_px": _median(mtf50_values),
        "sfr_mtf20_cy_px": _median([edge["mtf20_cy_px"] for edge in valid]),
        "sfr_mtf50_min_cy_px": float(min(mtf50_values)) if mtf50_values else None,
        "sfr_mtf50_max_cy_px": float(max(mtf50_values)) if mtf50_values else None,
        "sfr_mtf50_cv": float(np.std(mtf50_values) / mean50) if mean50 else None,
        "sfr_mtf50_by_target": {name: _median(values) for name, values in by_target.items()},
        "sfr_mtf50_by_group": group_median,
        "sfr_mtf50_horizontal_cy_px": _median(
            [edge["mtf50_cy_px"] for edge in valid if edge["sfr_direction"] == "horizontal"]),
        "sfr_mtf50_vertical_cy_px": _median(
            [edge["mtf50_cy_px"] for edge in valid if edge["sfr_direction"] == "vertical"]),
        "sfr_corner_center_ratio": float(corner / center) if center and corner else None,
        "sfr_image_height_px": int(rgb.shape[0]),
        # 线宽/图高 = 2 × cycles/pixel × 图像高度，便于对照行业常用的 LW/PH。
        "sfr_mtf50_lw_ph": 2.0 * _median(mtf50_values) * rgb.shape[0] if mtf50_values else None,
        "sfr_unit": "cycles/pixel",
    }


def _font(size):
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _save(image, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return str(path.resolve())


def annotate_sfr_targets(canonical_rgb, metrics, output_path):
    """在矫正平面上标出锁定的目标、各条斜边及其 MTF50。"""
    image = Image.fromarray(np.asarray(np.clip(canonical_rgb, 0, 255), dtype=np.uint8))
    draw = ImageDraw.Draw(image)
    image_array = np.asarray(image).copy()
    edge_labels = []
    font = _font(16)
    for target in metrics["sfr_targets"]:
        color = GROUP_COLORS.get(target["group"], (255, 40, 40))
        x0, y0, x1, y1 = target["window"]
        if not target.get("valid"):
            draw.rectangle((x0, y0, x1, y1), outline=(255, 0, 0), width=2)
            draw.text((x0 + 3, y0 + 3), f"{target['name']}: {target.get('error', '')[:24]}", fill=(255, 0, 0), font=font)
            continue
        draw.text((x0, max(0, y0 - 18)), target["name"], fill=color, font=font)
    for edge in metrics["sfr_edges"]:
        a, b = edge.get("fitted_canonical_segment", edge["canonical_segment"])
        ok = edge.get("valid")
        color = GROUP_COLORS.get(edge["group"], (255, 40, 40)) if ok else (255, 0, 0)
        cv2.line(
            image_array,
            tuple(np.round(a).astype(int)),
            tuple(np.round(b).astype(int)),
            color,
            thickness=3 if ok else 2,
            lineType=cv2.LINE_AA,
        )
        label = f"{edge['mtf50_cy_px']:.3f}" if ok and edge.get("mtf50_cy_px") is not None else "N/A"
        edge_labels.append((((a[0] + b[0]) / 2 + 4, (a[1] + b[1]) / 2 - 8), label, color))
    image = Image.fromarray(image_array)
    draw = ImageDraw.Draw(image)
    for position, label, color in edge_labels:
        draw.text(position, label, fill=color, font=font)
    return _save(image, output_path)


def save_sfr_edge_crops(rgb, metrics, output_dir, prefix):
    """每个目标保存一张"原图裁剪 | 带拟合边标注"的并排图，均为原图像素。"""
    saved = {}
    height, width = rgb.shape[:2]
    for target in metrics["sfr_targets"]:
        edges = [edge for edge in metrics["sfr_edges"] if edge["target"] == target["name"]]
        if not edges:
            continue
        points = np.array([edge[key] for edge in edges for key in ("p0_px", "p1_px")])
        pad = int(max(24, 0.15 * np.ptp(points, axis=0).max()))
        x0, y0 = int(max(0, points[:, 0].min() - pad)), int(max(0, points[:, 1].min() - pad))
        x1, y1 = int(min(width, points[:, 0].max() + pad)), int(min(height, points[:, 1].max() + pad))
        crop = Image.fromarray(np.asarray(np.clip(rgb[y0:y1, x0:x1], 0, 255), dtype=np.uint8))
        annotated = crop.copy()
        annotated_pixels = np.asarray(annotated).copy()
        edge_labels = []
        font = _font(max(14, crop.width // 28))
        for edge in edges:
            ok = edge.get("valid")
            color = GROUP_COLORS.get(edge["group"], (255, 40, 40)) if ok else (255, 0, 0)
            fitted_a = edge.get("fitted_edge_p0_px", edge["p0_px"])
            fitted_b = edge.get("fitted_edge_p1_px", edge["p1_px"])
            a = (fitted_a[0] - x0, fitted_a[1] - y0)
            b = (fitted_b[0] - x0, fitted_b[1] - y0)
            cv2.line(
                annotated_pixels,
                tuple(np.round(a).astype(int)),
                tuple(np.round(b).astype(int)),
                color,
                thickness=max(2, crop.width // 200),
                lineType=cv2.LINE_AA,
            )
            label = f"{edge['mtf50_cy_px']:.3f}" if ok and edge.get("mtf50_cy_px") is not None else "N/A"
            edge_labels.append((((a[0] + b[0]) / 2 + 4, (a[1] + b[1]) / 2 + 4), label, color))
        annotated = Image.fromarray(annotated_pixels)
        draw = ImageDraw.Draw(annotated)
        for position, label, color in edge_labels:
            draw.text(position, label, fill=color, font=font)
        sheet = Image.new("RGB", (crop.width * 2 + 8, crop.height), (255, 255, 255))
        sheet.paste(crop, (0, 0))
        sheet.paste(annotated, (crop.width + 8, 0))
        saved[target["name"]] = _save(sheet, Path(output_dir) / f"{prefix}_edge_{target['name']}.png")
    return saved


def _plot_curves(series, output_path, title, x_label, x_range, y_range, hlines=(), vlines=()):
    width, height = 1400, 820
    left, top, right, bottom = 110, 90, width - 40, height - 110
    image = Image.new("RGB", (width, height), (248, 250, 252))
    draw = ImageDraw.Draw(image)
    font = _font(15)
    draw.text((left, 24), title, fill=(20, 30, 45), font=_font(20))
    draw.text((left, height - 42), x_label, fill=(90, 100, 115), font=font)
    draw.rectangle((left, top, right, bottom), outline=(70, 80, 95), width=2)

    def xy(x, y):
        px = left + (x - x_range[0]) / (x_range[1] - x_range[0]) * (right - left)
        py = bottom - (y - y_range[0]) / (y_range[1] - y_range[0]) * (bottom - top)
        return px, py

    for level in hlines:
        py = xy(x_range[0], level)[1]
        draw.line((left, py, right, py), fill=(215, 220, 228), width=1)
        draw.text((left - 55, py - 8), f"{level:.1f}", fill=(80, 90, 105), font=font)
    for step in range(6):
        x = x_range[0] + (x_range[1] - x_range[0]) * step / 5.0
        px = xy(x, y_range[0])[0]
        draw.line((px, top, px, bottom), fill=(232, 235, 240), width=1)
        draw.text((px - 20, bottom + 12), f"{x:.2f}", fill=(80, 90, 105), font=font)
    for x, label in vlines:
        px = xy(x, y_range[0])[0]
        draw.line((px, top, px, bottom), fill=(200, 60, 60), width=2)
        draw.text((px + 6, top + 6), label, fill=(200, 60, 60), font=font)
    for group, points in series:
        color = GROUP_COLORS.get(group, (80, 80, 80))
        pixels = [xy(x, y) for x, y in points if x_range[0] <= x <= x_range[1]]
        if len(pixels) > 1:
            draw.line(pixels, fill=color, width=2)
    legend_y = top + 36
    for group, color in GROUP_COLORS.items():
        draw.line((right - 220, legend_y + 8, right - 190, legend_y + 8), fill=color, width=4)
        draw.text((right - 182, legend_y), group, fill=(40, 50, 65), font=font)
        legend_y += 24
    return _save(image, output_path)


def plot_sfr_curves(metrics, output_path):
    """所有有效斜边的 SFR 曲线；红线为 Nyquist，水平线为 0.5/0.2。"""
    series = [
        (edge["group"], [(p["frequency_cy_px"], p["mtf"]) for p in edge["sfr_curve"]])
        for edge in metrics["sfr_edges"] if edge.get("valid")
    ]
    median50 = metrics.get("sfr_mtf50_cy_px")
    title = "Slanted-edge SFR (all valid edges)"
    if median50 is not None:
        title += f" | median MTF50={median50:.4f} cycles/pixel"
    return _plot_curves(series, output_path, title, "frequency (cycles/pixel); red line = Nyquist 0.5",
                        (0.0, 1.0), (0.0, 1.2), hlines=(0.0, 0.2, 0.5, 1.0),
                        vlines=((NYQUIST_CY_PX, "Nyquist"),))


def plot_sfr_esf(metrics, output_path):
    """所有有效斜边的归一化 ESF，用于判断边缘是否被正确锁定。"""
    series = []
    half = 0.0
    for edge in metrics["sfr_edges"]:
        if edge.get("valid"):
            points = [(p["distance_px"], p["value"]) for p in edge["esf_curve"]]
            series.append((edge["group"], points))
            half = max(half, max(abs(x) for x, _ in points))
    half = max(half, 4.0)
    return _plot_curves(series, output_path, "Normalized ESF (all valid edges)",
                        "distance from fitted edge (pixel)", (-half, half), (-0.2, 1.2),
                        hlines=(0.0, 0.5, 1.0))
