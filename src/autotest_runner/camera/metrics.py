"""第一版图像统计指标。阈值需在固定光源、距离、图卡和分辨率下标定。

亮度使用解码后 8-bit RGB 的加权值，并非线性辐照度；Laplacian 方差
只是清晰度代理指标，不等同于 MTF。偏色/色块检测适用于中性均匀场。
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

try:
    import cv2
except ImportError:  # 允许旧环境继续使用 Pillow 基础算法
    cv2 = None


def opencv_available():
    """返回 OpenCV 是否可用，供后续色卡/棋盘格检测选择增强路径。"""
    return cv2 is not None


def opencv_edges(rgb, threshold1=80, threshold2=160):
    """使用 OpenCV Canny 返回边缘图，后续清晰度与测试卡定位共用。"""
    if cv2 is None:
        raise RuntimeError("OpenCV 未安装，请执行 pip install opencv-python-headless")
    image = np.asarray(np.clip(rgb, 0, 255), dtype=np.uint8)
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    return cv2.Canny(gray, threshold1, threshold2)


def _order_quad(points):
    """Return quadrilateral points as top-left, top-right, bottom-right, bottom-left."""
    points = np.asarray(points, dtype=np.float32).reshape(4, 2)
    sums = points.sum(axis=1)
    deltas = points[:, 0] - points[:, 1]
    return np.asarray([
        points[np.argmin(sums)],
        points[np.argmax(deltas)],
        points[np.argmax(sums)],
        points[np.argmin(deltas)],
    ], dtype=np.float32)


def _quad_aspect(points):
    """Estimate the aspect ratio of an ordered quadrilateral."""
    points = np.asarray(points, dtype=np.float32).reshape(4, 2)
    width = (np.linalg.norm(points[1] - points[0])
             + np.linalg.norm(points[2] - points[3])) / 2.0
    height = (np.linalg.norm(points[3] - points[0])
              + np.linalg.norm(points[2] - points[1])) / 2.0
    return float(width / max(height, 1e-6))


def _refine_quad_by_edges(contour, quad):
    """Fit a line to the contour points along each quad edge and intersect them."""
    points = contour.reshape(-1, 2).astype(np.float32)
    lines = []
    for index in range(4):
        start, end = quad[index], quad[(index + 1) % 4]
        direction = end - start
        length = float(np.linalg.norm(direction))
        if length < 1.0:
            return quad
        unit = direction / length
        normal = np.array([-unit[1], unit[0]], dtype=np.float32)
        relative = points - start
        along = relative @ unit
        across = np.abs(relative @ normal)
        keep = (along > length * 0.10) & (along < length * 0.90) & (across < length * 0.04)
        if int(keep.sum()) < 10:
            return quad
        vx, vy, x0, y0 = cv2.fitLine(points[keep], cv2.DIST_HUBER, 0, 0.01, 0.01).ravel()
        lines.append((np.array([x0, y0], dtype=np.float64), np.array([vx, vy], dtype=np.float64)))
    refined = []
    for index in range(4):
        p1, d1 = lines[index - 1]
        p2, d2 = lines[index]
        matrix = np.array([[d1[0], -d2[0]], [d1[1], -d2[1]]])
        if abs(np.linalg.det(matrix)) < 1e-6:
            return quad
        t = np.linalg.solve(matrix, p2 - p1)
        refined.append(p1 + t[0] * d1)
    refined = np.asarray(refined, dtype=np.float32)
    if np.linalg.norm(refined - quad, axis=1).max() > 0.05 * max(np.ptp(quad[:, 0]), np.ptp(quad[:, 1])):
        return quad
    return refined


def _border_contrast(gray, quad):
    """Brightness inside the quad minus a band just outside (chart has a dark frame)."""
    mask = np.zeros(gray.shape, dtype=np.uint8)
    cv2.fillConvexPoly(mask, np.round(quad).astype(np.int32), 255)
    band_width = max(5, int(min(gray.shape) * 0.02))
    kernel = np.ones((band_width * 2 + 1,) * 2, dtype=np.uint8)
    outer = cv2.dilate(mask, kernel) & ~cv2.dilate(mask, np.ones((3, 3), dtype=np.uint8))
    inner = cv2.erode(mask, kernel)
    if not outer.any() or not inner.any():
        return 0.0
    return float(gray[inner > 0].mean() - gray[outer > 0].mean())


def detect_chart_quad(rgb):
    """Locate the bright printable plane of the vendor resolution chart.

    The supplied chart has a dark border and a bright inner field containing
    the Siemens stars and the corner registration marks.  Thresholding several
    brightness percentiles and rejecting contours touching the camera frame is
    more stable for photographs of a monitor than a fixed image-space ROI.
    The returned quadrilateral is ordered clockwise from the top-left corner.
    """
    if cv2 is None:
        return {
            "valid": False,
            "method": "opencv_unavailable",
            "error": "OpenCV is required for chart localization",
        }
    image = np.asarray(np.clip(rgb, 0, 255), dtype=np.uint8)
    if image.ndim != 3 or image.shape[2] != 3:
        return {"valid": False, "method": "invalid_image", "error": "RGB image required"}
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    height, width = gray.shape
    image_area = float(width * height)
    candidates = []
    # The threshold is deliberately relative: monitor brightness and exposure
    # differ substantially between the two current validation photographs.
    for percentile in np.linspace(48, 92, 12):
        threshold = float(np.percentile(gray, percentile))
        # THRESH_BINARY is strict; subtracting one keeps a flat white field
        # usable when the percentile lands exactly on its quantized value.
        _, mask = cv2.threshold(gray, max(0.0, threshold - 1.0), 255, cv2.THRESH_BINARY)
        kernel = np.ones((max(5, int(round(min(height, width) / 250)) * 2 + 1),) * 2,
                        dtype=np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = float(cv2.contourArea(contour))
            if area < image_area * 0.20 or area > image_area * 0.88:
                continue
            perimeter = cv2.arcLength(contour, True)
            polygon = cv2.approxPolyDP(contour, max(2.0, perimeter * 0.03), True)
            if len(polygon) != 4 or not cv2.isContourConvex(polygon):
                continue
            quad = _order_quad(polygon.reshape(4, 2))
            aspect = _quad_aspect(quad)
            if not 1.30 <= aspect <= 2.70:
                continue
            x, y, box_width, box_height = cv2.boundingRect(polygon)
            margin = min(x, y, width - (x + box_width), height - (y + box_height))
            if margin < max(3, int(min(height, width) * 0.005)):
                continue
            # Prefer the largest plausible chart plane.  The aspect term only
            # breaks ties; it must not force a fixed camera framing.
            aspect_score = max(0.25, 1.0 - abs(math.log(aspect / 1.95)))
            quad = _refine_quad_by_edges(contour, quad)
            # A real chart sits inside a dark frame; merged bright backgrounds do not.
            contrast = _border_contrast(gray, quad)
            contrast_score = min(1.0, max(0.05, contrast / 60.0))
            score = (area / image_area) * aspect_score * contrast_score
            candidates.append({
                "quad": quad,
                "area_fraction": area / image_area,
                "aspect": aspect,
                "margin_px": int(margin),
                "score": float(score),
                "method": f"bright_chart_percentile_{percentile:.0f}",
                "threshold": threshold,
            })
    if not candidates:
        return {
            "valid": False,
            "method": "bright_chart_not_found",
            "error": "unable to find a four-corner chart plane",
        }
    best = max(candidates, key=lambda item: item["score"])
    confidence = min(1.0, best["score"] / 0.50)
    # 保留去重后的候选，供上层用图卡特征验证“最高分”是否真是图卡。
    distinct = []
    tolerance = 0.015 * max(width, height)
    for item in sorted(candidates, key=lambda entry: -entry["score"]):
        if all(np.abs(item["quad"] - kept["quad"]).max() > tolerance for kept in distinct):
            distinct.append(item)
        if len(distinct) >= 8:
            break
    return {
        "valid": True,
        "method": best["method"],
        "confidence": float(confidence),
        "quad_image_px": best["quad"].round(3).tolist(),
        "area_fraction": float(best["area_fraction"]),
        "aspect": float(best["aspect"]),
        "margin_px": best["margin_px"],
        "threshold": float(best["threshold"]),
        "candidates": [
            {
                "valid": True,
                "quad_image_px": item["quad"].round(3).tolist(),
                "confidence": float(min(1.0, item["score"] / 0.50)),
                "area_fraction": float(item["area_fraction"]),
                "aspect": float(item["aspect"]),
                "margin_px": item["margin_px"],
                "threshold": float(item["threshold"]),
                "method": item["method"],
            }
            for item in distinct
        ],
    }


def rectify_chart(rgb, canonical_size=(1800, 1000), detection=None):
    """Rectify a photographed chart to a deterministic canonical plane."""
    detection = detection or detect_chart_quad(rgb)
    if not detection.get("valid"):
        return {
            **detection,
            "rgb": np.asarray(rgb, dtype=float),
            "canonical_size": [int(canonical_size[0]), int(canonical_size[1])],
        }
    width, height = int(canonical_size[0]), int(canonical_size[1])
    if width < 128 or height < 128:
        raise ValueError("canonical chart size must be at least 128x128")
    source = np.asarray(np.clip(rgb, 0, 255), dtype=np.uint8)
    source_quad = np.asarray(detection["quad_image_px"], dtype=np.float32)
    target_quad = np.asarray([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
                             dtype=np.float32)
    transform = cv2.getPerspectiveTransform(source_quad, target_quad)
    rectified = cv2.warpPerspective(source, transform, (width, height),
                                    flags=cv2.INTER_CUBIC,
                                    borderMode=cv2.BORDER_REPLICATE)
    return {
        **detection,
        "rgb": rectified.astype(float),
        "canonical_size": [width, height],
        "quad_canonical_px": target_quad.round(3).tolist(),
        "perspective_transform": transform.round(8).tolist(),
    }


def decode(path):
    """完整解码以发现截断/损坏，按 EXIF 方向获取实际显示尺寸。"""
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"图片不存在: {path}")
    with Image.open(path) as source:
        source.load()
        if source.mode not in ("RGB", "RGBA", "L", "P"):
            raise ValueError(f"第一版仅支持 8-bit 图片，当前模式: {source.mode}")
        rgb = np.asarray(ImageOps.exif_transpose(source).convert("RGB"), dtype=np.float64)
    if min(rgb.shape[:2]) < 32:
        raise ValueError("图片宽高至少为 32 像素，保证 ROI 有效")
    return rgb


def luminance(rgb):
    return rgb @ np.array([0.299, 0.587, 0.114])


def image_size(rgb):
    """仅取图像尺寸；解析和分辨率用例无需计算其他 IQ 指标。"""
    return {"width": int(rgb.shape[1]), "height": int(rgb.shape[0])}


def regions(array, fraction=0.25):
    """中心与四角使用相同尺寸 ROI，保持不同区域的可比性。"""
    h, w = array.shape[:2]
    rh, rw = max(3, int(h * fraction)), max(3, int(w * fraction))
    y, x = (h - rh) // 2, (w - rw) // 2
    return {"center": array[y:y+rh, x:x+rw], "top_left": array[:rh, :rw],
            "top_right": array[:rh, -rw:], "bottom_left": array[-rh:, :rw],
            "bottom_right": array[-rh:, -rw:]}


def sharpness(gray):
    """不填充边界的离散 Laplacian 方差，避免边缘填充产生假清晰度。"""
    lap = (gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2]
           + gray[1:-1, 2:] - 4 * gray[1:-1, 1:-1])
    return float(lap.var())


def exposure_metrics(rgb):
    """曝光与异常帧共用：亮度均值、波动及极暗/极亮占比。"""
    gray = luminance(rgb)
    return {
        "mean_luma": float(gray.mean()), "std_luma": float(gray.std()),
        "under_ratio": float((gray <= 10).mean()),
        "over_ratio": float((gray >= 245).mean()),
    }


def exposure_percentiles(rgb):
    """返回曝光分布的关键亮度分位数，供固定场景的 AE 门禁使用。"""
    gray = luminance(rgb)
    values = np.percentile(gray, [1, 5, 50, 95, 99])
    return {
        "luma_p1": float(values[0]),
        "luma_p5": float(values[1]),
        "luma_p50": float(values[2]),
        "luma_p95": float(values[3]),
        "luma_p99": float(values[4]),
    }


def exposure_median(rgb):
    """返回亮度中位数，降低少量极端像素对曝光判断的影响。"""
    return {"median_luma": float(np.median(luminance(rgb)))}


def exposure_distribution(rgb):
    """返回有效动态范围、RMS对比度和亮度直方图熵。"""
    gray = luminance(rgb)
    histogram, _ = np.histogram(gray, bins=256, range=(0, 256))
    probabilities = histogram[histogram > 0] / gray.size
    return {
        "effective_dynamic_range": float(np.percentile(gray, 95) - np.percentile(gray, 5)),
        "rms_contrast": float(gray.std()),
        "histogram_entropy": float(-(probabilities * np.log2(probabilities)).sum()),
    }


def output_format_metrics(path):
    """读取原始文件格式、通道数、位深和 EXIF 方向。"""
    with Image.open(path) as source:
        exif = source.getexif()
        return {
            "format": source.format or "",
            "mode": source.mode,
            "channels": len(source.getbands()),
            "bit_depth": 16 if source.mode.startswith("I;16") else 8,
            "exif_orientation": int(exif.get(274, 1)),
        }


def sharpness_metrics(rgb):
    """清晰度用例共用：全图和中心/四角 Laplacian 方差。"""
    gray = luminance(rgb)
    rois = regions(gray)
    scores = {k: sharpness(v) for k, v in rois.items()}
    return {
        "global_sharpness": sharpness(gray), "roi_sharpness": scores,
        "sharpness_ratio": min(scores.values()) / max(max(scores.values()), 1e-9),
    }


def _bilinear_sample(gray, x, y):
    """在灰度图上做双线性采样，供圆环/斜边频率测量使用。"""
    h, w = gray.shape
    x = np.clip(np.asarray(x, dtype=float), 0, w - 1)
    y = np.clip(np.asarray(y, dtype=float), 0, h - 1)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    x1, y1 = np.minimum(x0 + 1, w - 1), np.minimum(y0 + 1, h - 1)
    wx, wy = x - x0, y - y0
    return ((1 - wx) * (1 - wy) * gray[y0, x0]
            + wx * (1 - wy) * gray[y0, x1]
            + (1 - wx) * wy * gray[y1, x0]
            + wx * wy * gray[y1, x1])


def _mtf_crossing(frequencies, modulation, level):
    """返回 MTF 曲线第一次跌破 level 的频率；没有交点时返回 None。"""
    for index in range(1, len(frequencies)):
        previous, current = modulation[index - 1], modulation[index]
        if previous >= level > current:
            f0, f1 = frequencies[index - 1], frequencies[index]
            if current == previous:
                return float(f1)
            fraction = (level - previous) / (current - previous)
            return float(f0 + fraction * (f1 - f0))
    return None


def _monotonic_decreasing(values):
    """Fit a non-increasing envelope without letting one noisy sample dominate."""
    blocks = []
    for value in np.asarray(values, dtype=float):
        blocks.append([float(value), 1])
        while len(blocks) >= 2 and blocks[-2][0] < blocks[-1][0]:
            right_value, right_count = blocks.pop()
            left_value, left_count = blocks.pop()
            total = left_count + right_count
            blocks.append([
                (left_value * left_count + right_value * right_count) / total,
                total,
            ])
    return np.asarray([value for value, count in blocks for _ in range(count)], dtype=float)


def _siemens_center_score(gray, center_x, center_y, radius, cycles):
    """Score how well a candidate point is the center of a Siemens star."""
    height, width = gray.shape
    if (center_x - radius < 1 or center_x + radius >= width - 1
            or center_y - radius < 1 or center_y + radius >= height - 1):
        return -1.0
    sample_count = max(256, min(720, cycles * 12))
    theta = np.arange(sample_count, dtype=float) * (2 * np.pi / sample_count)
    harmonic = np.exp(-1j * cycles * theta)
    scores = []
    for current_radius in np.linspace(radius * 0.35, radius * 0.88, 8):
        values = _bilinear_sample(
            gray,
            center_x + current_radius * np.cos(theta),
            center_y + current_radius * np.sin(theta),
        )
        contrast = float(np.percentile(values, 95) - np.percentile(values, 5))
        if contrast < 2.0:
            continue
        amplitude = abs(np.mean((values - values.mean()) * harmonic))
        scores.append(float(amplitude / max(contrast, 1e-6)))
    return float(np.median(scores)) if scores else -1.0


def _refine_siemens_star_center(gray, center_x, center_y, radius, cycles):
    """Refine a plan anchor to the local Siemens-star center.

    The plan coordinates are intentionally only anchors.  A chart can be
    resampled and slightly distorted even after perspective rectification, so
    using the anchor as the final ROI center is unsafe.  The search is limited
    around the configured location to avoid unrelated radial patterns.
    """
    search_radius = max(24.0, min(radius * 2.0, min(gray.shape) * 0.15))

    def search(anchor_x, anchor_y, half_width, step):
        values = []
        x_start = int(round(anchor_x - half_width))
        x_stop = int(round(anchor_x + half_width))
        y_start = int(round(anchor_y - half_width))
        y_stop = int(round(anchor_y + half_width))
        for candidate_y in range(y_start, y_stop + 1, step):
            for candidate_x in range(x_start, x_stop + 1, step):
                score = _siemens_center_score(
                    gray, candidate_x, candidate_y, radius, cycles
                )
                values.append((score, candidate_x, candidate_y))
        return max(values, default=(-1.0, anchor_x, anchor_y))

    coarse = search(center_x, center_y, search_radius, max(2, int(round(radius * 0.06))))
    fine = search(coarse[1], coarse[2], max(4.0, radius * 0.10), 1)
    return float(fine[1]), float(fine[2]), float(fine[0]), float(search_radius)


def _siemens_star_region(gray, region):
    """测量一颗西门子星的径向调制度曲线。

    region 使用归一化坐标：x/y 是图像宽高比例，radius 是短边比例，
    cycles 是整圈黑白周期数。它适合用户提供的旧式 ISO/CIPA 图卡，
    但不等同于 ISO 12233:2014/2023 eSFR 的标准自动检测流程。
    """
    name = str(region.get("name", "star"))
    try:
        cx = float(region["x"])
        cy = float(region["y"])
        radius_fraction = float(region["radius"])
        cycles = int(region["cycles"])
    except (KeyError, TypeError, ValueError) as exc:
        return {"name": name, "valid": False, "error": f"配置无效: {exc}"}

    h, w = gray.shape
    radius = radius_fraction * min(h, w)
    configured_center_x, configured_center_y = cx * w, cy * h
    if not (0 < cx < 1 and 0 < cy < 1 and 0 < radius_fraction < 0.5 and cycles >= 2):
        return {"name": name, "valid": False, "error": "x/y/radius/cycles 超出范围"}
    if (configured_center_x - radius < 1 or configured_center_x + radius >= w - 1
            or configured_center_y - radius < 1 or configured_center_y + radius >= h - 1):
        return {"name": name, "valid": False, "error": "圆形 ROI 超出图像边界"}

    center_x, center_y, center_score, search_radius = _refine_siemens_star_center(
        gray, configured_center_x, configured_center_y, radius, cycles
    )
    # 实测真星得分约 0.12-0.23；文字/背景纹理仅 0.03-0.05。
    if center_score < 0.08:
        return {
            "name": name,
            "valid": False,
            "error": "未找到具有足够径向调制度的完整西门子星",
            "configured_center_px": [float(configured_center_x), float(configured_center_y)],
            "center_px": [float(center_x), float(center_y)],
            "center_score": float(center_score),
        }

    sample_count = max(512, cycles * 64)
    theta = np.arange(sample_count, dtype=float) * (2 * np.pi / sample_count)
    radii = np.linspace(radius * 0.08, radius * 0.92, 48)
    frequencies, modulations = [], []
    for current_radius in radii[::-1]:
        values = _bilinear_sample(
            gray,
            center_x + current_radius * np.cos(theta),
            center_y + current_radius * np.sin(theta),
        )
        mean = float(values.mean())
        contrast = float(np.percentile(values, 95) - np.percentile(values, 5))
        if mean <= 1e-6 or contrast < 1.0:
            continue
        harmonic = np.abs(np.mean((values - mean) * np.exp(-1j * cycles * theta)))
        modulation = float(2.0 * harmonic / mean)
        frequencies.append(float(cycles / (2 * np.pi * current_radius)))
        modulations.append(modulation)

    if len(frequencies) < 8:
        return {"name": name, "valid": False, "error": "有效圆环不足"}
    frequencies = np.asarray(frequencies, dtype=float)
    modulations = np.asarray(modulations, dtype=float)
    baseline_count = max(3, len(modulations) // 5)
    baseline = float(np.median(modulations[:baseline_count]))
    # 真星低频调制度约 0.4-0.8；过低说明 ROI 内没有黑白扇形，归一化会放大噪声。
    if not math.isfinite(baseline) or baseline < 0.15:
        return {
            "name": name,
            "valid": False,
            "error": f"低频调制度过低({baseline:.3f})，ROI 内不是有效西门子星",
            "center_px": [float(center_x), float(center_y)],
            "center_score": float(center_score),
            "low_frequency_modulation": baseline,
        }
    # MTF is normalized to the low-frequency response.  Screen moire can make
    # a raw sample exceed one; retain the raw value for diagnostics but keep
    # the plotted/fitted MTF in the physical [0, 1] range.
    normalized_modulation = modulations / baseline
    raw_modulation = np.clip(normalized_modulation, 0.0, 1.5)
    # Screen capture moire and JPEG ringing can make adjacent samples rise
    # again.  MTF50/MTF20 are defined on a decreasing response, so use an
    # isotonic decreasing fit for crossings while preserving raw samples.
    modulation = _monotonic_decreasing(np.clip(normalized_modulation, 0.0, 1.0))
    mtf50_crossing = _mtf_crossing(frequencies, modulation, 0.5)
    mtf20_crossing = _mtf_crossing(frequencies, modulation, 0.2)
    # Frequencies above 0.5 cycles/pixel are beyond the sampled image's
    # Nyquist limit.  Keep the raw crossing for diagnostics but never expose
    # it as a physical MTF50/MTF20 result.
    nyquist_cy_px = 0.5
    mtf50 = mtf50_crossing if mtf50_crossing is not None and mtf50_crossing <= nyquist_cy_px else None
    mtf20 = mtf20_crossing if mtf20_crossing is not None and mtf20_crossing <= nyquist_cy_px else None
    bounds = [
        max(0, int(round(center_x - radius))),
        max(0, int(round(center_y - radius))),
        min(w, int(round(center_x + radius))),
        min(h, int(round(center_y + radius))),
    ]
    return {
        "name": name,
        "valid": True,
        "configured_center": [cx, cy],
        "center": [float(center_x / w), float(center_y / h)],
        "configured_center_px": [float(configured_center_x), float(configured_center_y)],
        "center_px": [float(center_x), float(center_y)],
        "center_offset_px": [
            float(center_x - configured_center_x),
            float(center_y - configured_center_y),
        ],
        "center_score": float(center_score),
        "center_search_radius_px": float(search_radius),
        "radius": radius_fraction,
        "radius_px": float(radius),
        "roi_bounds_px": bounds,
        "cycles": cycles,
        "edge_contrast": float(np.max(modulations)),
        "low_frequency_modulation": baseline,
        "frequency_curve": [
            {
                "frequency_cy_px": float(frequency),
                "mtf": float(value),
                "mtf_raw": float(raw_value),
            }
            for frequency, value, raw_value in zip(frequencies, modulation, raw_modulation)
        ],
        "frequency_min_cy_px": float(frequencies.min()),
        "frequency_max_cy_px": float(frequencies.max()),
        "nyquist_cy_px": nyquist_cy_px,
        "mtf50_crossing_cy_px": mtf50_crossing,
        "mtf20_crossing_cy_px": mtf20_crossing,
        "mtf50_cy_px": mtf50,
        "mtf20_cy_px": mtf20,
    }


def siemens_star_mtf(rgb, regions_config):
    """从手工标注的西门子星 ROI 估计 MTF50/MTF20。

    结果单位统一为 cycles/pixel。超过 Nyquist 的交点仅保留在区域诊断字段中。
    这是一条面向旧式高反差图卡的可复现实验路径；正式 eSFR 验收仍需
    具备物理尺寸、低对比度斜边和标准 ROI 的 ISO 12233 图卡。
    """
    if not isinstance(regions_config, list) or not regions_config:
        raise ValueError("请配置 SFR_STAR_REGIONS：至少提供一颗星的归一化 x/y/radius/cycles")
    gray = luminance(rgb)
    regions = [_siemens_star_region(gray, region) for region in regions_config]
    valid = [item for item in regions if item.get("valid")]
    mtf50 = [item["mtf50_cy_px"] for item in valid if item["mtf50_cy_px"] is not None]
    mtf20 = [item["mtf20_cy_px"] for item in valid if item["mtf20_cy_px"] is not None]
    return {
        "siemens_star_regions": regions,
        "siemens_star_configured_count": len(regions),
        "siemens_star_valid_count": len(valid),
        "siemens_star_mtf50_by_region": {
            item["name"]: item["mtf50_cy_px"] for item in valid
        },
        "siemens_star_mtf20_by_region": {
            item["name"]: item["mtf20_cy_px"] for item in valid
        },
        "siemens_star_mtf50_cy_px": float(np.median(mtf50)) if mtf50 else None,
        "siemens_star_mtf20_cy_px": float(np.median(mtf20)) if mtf20 else None,
        "siemens_star_mtf_unit": "cycles/pixel",
    }


def annotate_siemens_star_regions(rgb, regions_config, output_path):
    """把实际参与计算的西门子星圆形 ROI 画到原图上并保存。"""
    image = Image.fromarray(np.asarray(np.clip(rgb, 0, 255), dtype=np.uint8))
    draw = ImageDraw.Draw(image)
    h, w = rgb.shape[:2]
    for index, region in enumerate(regions_config, start=1):
        try:
            cx, cy = float(region["x"]) * w, float(region["y"]) * h
            radius = float(region["radius"]) * min(h, w)
            name = str(region.get("name", f"star_{index}"))
            cycles = int(region["cycles"])
        except (KeyError, TypeError, ValueError):
            continue
        box = (cx - radius, cy - radius, cx + radius, cy + radius)
        draw.ellipse(box, outline=(255, 40, 40), width=max(2, round(min(h, w) / 400)))
        draw.line((cx - radius * 0.12, cy, cx + radius * 0.12, cy), fill=(255, 40, 40), width=2)
        draw.line((cx, cy - radius * 0.12, cx, cy + radius * 0.12), fill=(255, 40, 40), width=2)
        draw.text((cx - radius, max(0, cy - radius - 22)), f"{name} | {cycles} cycles", fill=(255, 40, 40))
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() in {".jpg", ".jpeg"}:
        image.save(output_path, quality=90, optimize=True)
    else:
        image.save(output_path)
    return str(output_path.resolve())


def annotate_siemens_star_metrics(rgb, metrics, output_path):
    """Annotate exactly the ROI bounds used by the MTF calculation."""
    image = Image.fromarray(np.asarray(np.clip(rgb, 0, 255), dtype=np.uint8))
    draw = ImageDraw.Draw(image)
    h, w = rgb.shape[:2]
    for index, region in enumerate(metrics.get("siemens_star_regions", []), start=1):
        bounds = region.get("roi_bounds_px")
        center = region.get("center_px")
        if not bounds or not center:
            continue
        x0, y0, x1, y1 = [int(round(value)) for value in bounds]
        cx, cy = [float(value) for value in center]
        name = str(region.get("name", f"star_{index}"))
        color = (255, 40, 40) if region.get("valid") else (255, 150, 20)
        draw.rectangle((x0, y0, x1, y1), outline=color, width=max(2, round(min(h, w) / 450)))
        draw.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), fill=color)
        label = f"{name} | {region.get('cycles', '?')} cycles"
        draw.text((x0, max(0, y0 - 22)), label, fill=color)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return str(output_path.resolve())


def save_siemens_star_crops(rgb, metrics, output_dir, prefix):
    """Save one raw local crop per selected Siemens-star ROI."""
    image = Image.fromarray(np.asarray(np.clip(rgb, 0, 255), dtype=np.uint8))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    saved = {}
    for index, region in enumerate(metrics.get("siemens_star_regions", []), start=1):
        bounds = region.get("roi_bounds_px")
        if not bounds:
            continue
        x0, y0, x1, y1 = [int(round(value)) for value in bounds]
        side = max(x1 - x0, y1 - y0, 16)
        padding = max(8, int(round(side * 0.18)))
        crop_box = (
            max(0, x0 - padding), max(0, y0 - padding),
            min(image.width, x1 + padding), min(image.height, y1 + padding),
        )
        name = str(region.get("name", f"star_{index}"))
        safe_name = "".join(character if character.isalnum() or character in "-_" else "_"
                            for character in name).strip("_") or f"star_{index}"
        path = output_dir / f"{prefix}_roi_{safe_name}.png"
        image.crop(crop_box).save(path)
        saved[name] = str(path.resolve())
    return saved


def save_rgb_image(rgb, output_path):
    """Save an RGB ndarray as a report artifact and return its absolute path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.asarray(np.clip(rgb, 0, 255), dtype=np.uint8)).save(output_path)
    return str(output_path.resolve())


def annotate_chart_quad(rgb, detection, output_path):
    """Save the original photograph with the detected chart plane outlined."""
    image = Image.fromarray(np.asarray(np.clip(rgb, 0, 255), dtype=np.uint8))
    draw = ImageDraw.Draw(image)
    quad = detection.get("quad_image_px") or []
    if len(quad) == 4:
        points = [(float(point[0]), float(point[1])) for point in quad]
        draw.line(points + [points[0]], fill=(255, 40, 40), width=max(3, round(min(image.size) / 350)))
        for index, (x, y) in enumerate(points, start=1):
            draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill=(255, 40, 40))
            draw.text((x + 10, y + 10), f"C{index}", fill=(255, 40, 40))
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() in {".jpg", ".jpeg"}:
        image.save(output_path, quality=90, optimize=True)
    else:
        image.save(output_path)
    return str(output_path.resolve())


def plot_siemens_star_mtf(metrics, output_path):
    """Save a compact, self-contained MTF curve plot for the execution report."""
    width, height = 1400, 820
    margin_left, margin_right = 110, 40
    margin_top, margin_bottom = 90, 110
    chart_left = margin_left
    chart_top = margin_top
    chart_right = width - margin_right
    chart_bottom = height - margin_bottom
    image = Image.new("RGB", (width, height), (248, 250, 252))
    draw = ImageDraw.Draw(image)

    draw.text((chart_left, 24), "Siemens-star MTF response", fill=(20, 30, 45))
    draw.text((chart_left, 51), "monotonic envelope; frequency = cycles/pixel", fill=(90, 100, 115))
    draw.rectangle((chart_left, chart_top, chart_right, chart_bottom), outline=(70, 80, 95), width=2)

    regions = [item for item in metrics.get("siemens_star_regions", []) if item.get("valid")]
    nyquist = 0.5
    frequencies = [
        point.get("frequency_cy_px")
        for region in regions
        for point in region.get("frequency_curve", [])
        if point.get("frequency_cy_px") is not None
        and point.get("frequency_cy_px") <= nyquist
    ]
    max_frequency = nyquist
    curve_values = [
        point.get("mtf")
        for region in regions
        for point in region.get("frequency_curve", [])
        if point.get("mtf") is not None
        and point.get("frequency_cy_px") is not None
        and point.get("frequency_cy_px") <= nyquist
    ]
    max_modulation = max(curve_values, default=1.0)
    max_modulation = max(1.05, min(2.0, max_modulation * 1.05))

    def point_xy(frequency, value):
        x = chart_left + (float(frequency) / max_frequency) * (chart_right - chart_left)
        y = chart_bottom - (float(value) / max_modulation) * (chart_bottom - chart_top)
        return int(round(x)), int(round(y))

    for level in (0.0, 0.2, 0.5, 1.0):
        y = point_xy(0.0, level)[1]
        draw.line((chart_left, y, chart_right, y), fill=(215, 220, 228), width=1)
        draw.text((chart_left - 55, y - 8), f"{level:.1f}", fill=(80, 90, 105))
    for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
        x = chart_left + int(round(fraction * (chart_right - chart_left)))
        draw.line((x, chart_top, x, chart_bottom), fill=(232, 235, 240), width=1)
        draw.text((x - 18, chart_bottom + 12), f"{max_frequency * fraction:.3f}", fill=(80, 90, 105))

    colors = [(30, 105, 190), (215, 85, 45), (35, 145, 85), (150, 75, 170), (190, 125, 30)]
    legend_x = chart_left + 20
    legend_y = chart_top + 18
    for index, region in enumerate(regions):
        color = colors[index % len(colors)]
        curve = [
            point for point in region.get("frequency_curve", [])
            if point.get("frequency_cy_px") is not None
            and point.get("frequency_cy_px") <= nyquist
        ]
        points = [
            point_xy(point["frequency_cy_px"], point["mtf"])
            for point in curve
            if point.get("frequency_cy_px") is not None and point.get("mtf") is not None
        ]
        if len(points) > 1:
            draw.line(points, fill=color, width=4)
        name = str(region.get("name", f"region_{index + 1}"))
        mtf50 = region.get("mtf50_cy_px")
        mtf20 = region.get("mtf20_cy_px")
        label = (
            f"{name}: MTF50={mtf50:.4f}  MTF20={mtf20:.4f} cycles/pixel"
            if mtf50 is not None and mtf20 is not None else f"{name}: N/A"
        )
        draw.line((legend_x, legend_y + 8, legend_x + 28, legend_y + 8), fill=color, width=4)
        draw.text((legend_x + 38, legend_y), label, fill=(40, 50, 65))
        legend_y += 28

    aggregate50 = metrics.get("siemens_star_mtf50_cy_px")
    aggregate20 = metrics.get("siemens_star_mtf20_cy_px")
    summary = (
        f"aggregate: MTF50={aggregate50:.4f}, MTF20={aggregate20:.4f} cycles/pixel"
        if aggregate50 is not None and aggregate20 is not None
        else "aggregate: N/A"
    )
    draw.text((chart_left, height - 64), "physical range: 0.000-0.500 cycles/pixel (Nyquist)", fill=(90, 100, 115))
    draw.text((chart_left, height - 42), summary, fill=(20, 30, 45))
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return str(output_path.resolve())


def sharpness_heatmap_3x3(rgb):
    """计算 3x3 等尺寸 ROI 的 Laplacian 方差热力图。"""
    gray = luminance(rgb)
    rows = np.array_split(gray, 3, axis=0)
    grid = [[sharpness(tile) for tile in np.array_split(row, 3, axis=1)] for row in rows]
    values = [value for row in grid for value in row]
    return {
        "sharpness_heatmap_3x3": grid,
        "sharpness_min": float(min(values)),
        "sharpness_max": float(max(values)),
        "sharpness_ratio": float(min(values) / max(max(values), 1e-9)),
    }


def tenengrad(rgb):
    """以 Sobel 梯度能量计算 Tenengrad 清晰度代理指标。"""
    gray = luminance(rgb)
    gx = gray[:, 2:] - gray[:, :-2]
    gy = gray[2:, :] - gray[:-2, :]
    return {"tenengrad": float((gx[1:-1, :] ** 2 + gy[:, 1:-1] ** 2).mean())}


def color_metrics(rgb):
    """AWB 用例共用：RGB 通道统计与粗略中性色偏。"""
    channels = rgb.mean(axis=(0, 1))
    return {
        "rgb_mean": channels.tolist(), "rgb_std": rgb.std(axis=(0, 1)).tolist(),
        "color_cast": float((channels.max() - channels.min()) / max(channels.mean(), 1e-9)),
        "red_green_ratio": float(channels[0] / max(channels[1], 1e-9)),
        "blue_green_ratio": float(channels[2] / max(channels[1], 1e-9)),
        "neutral_error": float(np.sqrt(((channels - channels.mean()) ** 2).mean())),
    }


def shading_metrics(rgb):
    """仅均匀场使用；返回中心/四角亮度和相对差值。"""
    rois = regions(luminance(rgb))
    means = {k: float(v.mean()) for k, v in rois.items()}
    corners = [v for k, v in means.items() if k != "center"]
    return {
        "roi_luma": means,
        "center_edge_delta": max(abs(means["center"] - v) for v in corners) / max(means["center"], 1e-9),
        "corner_delta": (max(corners) - min(corners)) / max(float(np.mean(corners)), 1e-9),
    }


def defect_metrics(rgb):
    """中性场大色块检测；不用于坏点或条纹判定。"""
    # 相对于每个像素的三通道均值计算色度；只用于中性场，避免把亮度变化当偏色。
    chroma = rgb - rgb.mean(axis=2, keepdims=True)
    baseline = np.median(chroma, axis=(0, 1))
    residual = np.max(np.abs(chroma - baseline), axis=2)
    # 8x8 分块，定位大面积色块/花屏；细粒度坏点留到后续专用用例。
    tiles = [float(tile.mean()) for row in np.array_split(residual, 8, axis=0)
             for tile in np.array_split(row, 8, axis=1)]
    return {"max_chroma_tile": max(tiles), "chroma_tiles": tiles}


def grid_metrics(rgb, grid=9):
    """Return luma and chroma statistics for an evenly split ROI grid."""
    gray = luminance(rgb)
    luma = [[float(tile.mean()) for tile in np.array_split(row, grid, axis=1)]
            for row in np.array_split(gray, grid, axis=0)]
    rg = rgb[:, :, 0] / np.maximum(rgb[:, :, 1], 1e-6)
    bg = rgb[:, :, 2] / np.maximum(rgb[:, :, 1], 1e-6)
    rg_grid = [[float(tile.mean()) for tile in np.array_split(row, grid, axis=1)]
               for row in np.array_split(rg, grid, axis=0)]
    bg_grid = [[float(tile.mean()) for tile in np.array_split(row, grid, axis=1)]
               for row in np.array_split(bg, grid, axis=0)]
    return {"luma_grid": luma, "rg_grid": rg_grid, "bg_grid": bg_grid,
            "luma_range": float(np.ptp(luma)), "rg_range": float(np.ptp(rg_grid)),
            "bg_range": float(np.ptp(bg_grid))}


def noise_metrics(rgb):
    """Estimate spatial noise in Y/Cb/Cr and signal-to-noise ratio."""
    y = luminance(rgb)
    cb = rgb[:, :, 2] - y
    cr = rgb[:, :, 0] - y
    luma_std, chroma_std = float(y.std()), float(np.sqrt((cb.var() + cr.var()) / 2))
    return {"luma_noise": luma_std, "chroma_noise": chroma_std,
            "signal_to_noise_ratio": float(y.mean() / max(luma_std, 1e-9)),
            "snr_db": float(20 * np.log10(max(y.mean(), 1e-9) / max(luma_std, 1e-9))),
            "mean_luma": float(y.mean())}


def defect_detail_metrics(rgb):
    """Detect isolated pixels and row/column periodicity in a flat field."""
    y = luminance(rgb)
    median = np.median(y)
    deviation = np.abs(y - median)
    mad = np.median(deviation)
    threshold = max(12.0, 8.0 * mad)
    hot = int(((y > median + threshold) & (y > 200)).sum())
    dead = int(((y < median - threshold) & (y < 30)).sum())
    row_means, col_means = y.mean(axis=1), y.mean(axis=0)
    row_band = float(np.std(row_means) / max(np.mean(y), 1e-9))
    col_band = float(np.std(col_means) / max(np.mean(y), 1e-9))
    return {"hot_pixel_count": hot, "dead_pixel_count": dead,
            "horizontal_banding": row_band, "vertical_banding": col_band,
            "median_luma": float(median)}


def geometry_metrics(rgb):
    """Provide basic grid/edge geometry proxies; not a calibrated lens model."""
    gray = luminance(rgb)
    h, w = gray.shape
    edges = opencv_edges(rgb) if cv2 is not None else np.zeros_like(gray, dtype=np.uint8)
    ys, xs = np.nonzero(edges)
    if len(xs) < 8:
        return {"edge_count": int(len(xs)), "optical_center_offset": float("inf"),
                "perspective_error": float("inf"), "lens_distortion": float("inf"),
                "lateral_chromatic_aberration": float("inf")}
    center_x, center_y = w / 2, h / 2
    optical_offset = float(np.hypot(xs.mean() - center_x, ys.mean() - center_y) / max(w, h))
    left, right = xs < center_x, xs >= center_x
    perspective = float(abs(ys[left].mean() - ys[right].mean()) / max(h, 1)) if left.any() and right.any() else float("inf")
    radius = np.hypot(xs - center_x, ys - center_y)
    distortion = float(np.std(radius) / max(np.mean(radius), 1e-9))
    chroma = rgb[:, :, 0].astype(float) - rgb[:, :, 1].astype(float)
    lca = float(np.mean(np.abs(np.gradient(chroma)[0])) + np.mean(np.abs(np.gradient(chroma)[1])))
    return {"edge_count": int(len(xs)), "optical_center_offset": optical_offset,
            "perspective_error": perspective, "lens_distortion": distortion,
            "lateral_chromatic_aberration": lca}


def compression_metrics(path, rgb):
    """Estimate JPEG block artifacts and expose the source format."""
    format_name = ""
    try:
        with Image.open(path) as source:
            format_name = source.format or ""
    except (OSError, ValueError):
        pass
    gray = luminance(rgb)
    block_edges = []
    for axis in (0, 1):
        strips = np.diff(gray, axis=axis)
        positions = range(7, strips.shape[axis], 8)
        values = [np.mean(np.abs(np.take(strips, pos, axis=axis))) for pos in positions]
        block_edges.extend(values)
    return {"format": format_name, "jpeg_blockiness": float(np.mean(block_edges)) if block_edges else 0.0}


def sequence_metrics(path, rgb):
    """Compare a configured image directory; one image is explicitly unavailable."""
    path = Path(path)
    candidates = sorted(p for p in (path.iterdir() if path.is_dir() else [])
                       if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"})
    if len(candidates) < 2:
        return {"available": False, "frame_count": 1, "duplicate_similarity": None,
                "temporal_noise": None}
    frames = [decode(item) for item in candidates]
    common_h = min(frame.shape[0] for frame in frames)
    common_w = min(frame.shape[1] for frame in frames)
    stack = np.stack([frame[:common_h, :common_w] for frame in frames])
    deltas = np.abs(np.diff(stack, axis=0))
    return {"available": True, "frame_count": len(frames),
            "duplicate_similarity": float(1.0 - deltas.mean() / 255.0),
            "temporal_noise": float(deltas.std())}


def baseline_metrics(path, rgb):
    """Compare the current image to a configured baseline file when available."""
    baseline = Path(path)
    if not baseline.is_file():
        return {"available": False, "baseline_delta": None, "baseline_similarity": None}
    reference = decode(baseline)
    h, w = min(reference.shape[0], rgb.shape[0]), min(reference.shape[1], rgb.shape[1])
    delta = np.abs(reference[:h, :w] - rgb[:h, :w])
    return {"available": True, "baseline_delta": float(delta.mean()),
            "baseline_similarity": float(1.0 - delta.mean() / 255.0)}


def measure(rgb):
    """聚合指标仅供算法回归测试和离线分析；业务脚本调用各自的小函数。"""
    return {
        **image_size(rgb), **exposure_metrics(rgb), **exposure_percentiles(rgb),
        **exposure_median(rgb), **exposure_distribution(rgb),
        "format": "", "mode": "RGB", "exif_orientation": 1, "bit_depth": 8,
        "channels": int(rgb.shape[2]) if rgb.ndim == 3 else 1,
        **sharpness_metrics(rgb), **sharpness_heatmap_3x3(rgb), **tenengrad(rgb),
        **color_metrics(rgb), **shading_metrics(rgb), **defect_metrics(rgb),
    }
