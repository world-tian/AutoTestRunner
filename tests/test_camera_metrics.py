"""用构造输入验证检测行为；不是设备实拍验收记录。"""
import json
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image, ImageFilter

from autotest_runner.camera.metrics import (
    baseline_metrics, compression_metrics, decode, exposure_median, exposure_percentiles,
    geometry_metrics, grid_metrics, measure, noise_metrics, sequence_metrics,
    detect_chart_quad, plot_siemens_star_mtf, rectify_chart, save_siemens_star_crops,
    sharpness_heatmap_3x3, siemens_star_mtf,
)
from autotest_runner.camera.execution import load_config, load_limits
from autotest_runner.core.runner import _resolve_junit_case_id
from autotest_runner.core.sync import collect_cases, sync_cases


def texture():
    y, x = np.indices((128, 128))
    gray = np.where((x // 4 + y // 4) % 2, 170, 90).astype(np.uint8)
    return np.repeat(gray[:, :, None], 3, axis=2)


ROOT = Path(__file__).parents[1] / 'testcases/camera'
CATALOG = {row['local_case_id']: row for row in json.loads((ROOT / 'catalog.json').read_text(encoding='utf-8'))}


def case_module(cid):
    path = ROOT / CATALOG[cid]['script_path']
    spec = importlib.util.spec_from_file_location('camera_case_' + cid.replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def result(cid, rgb, size=None):
    case = case_module(cid)
    limits = load_limits(ROOT / 'common.json', case.CASE_LIMITS)
    return case.check(measure(rgb.astype(float)), limits, size or [128, 128])[0]


@pytest.mark.parametrize('cid', ['CAM-IMG-001','CAM-IMG-002','CAM-IMG-003','CAM-IMG-004','CAM-IMG-005', 'CAM-AE-001','CAM-AE-002','CAM-AE-003','CAM-AE-005','CAM-AE-006','CAM-AE-007','CAM-AE-008','CAM-AE-009',
    'CAM-SHP-001','CAM-SHP-002','CAM-SHP-003','CAM-SHP-004','CAM-SHP-005','CAM-SHP-006','CAM-COLOR-001','CAM-COLOR-002','CAM-SHD-001','CAM-SHD-002','CAM-DEFECT-004'])
def test_reference_texture_passes(cid):
    assert result(cid, texture())


@pytest.mark.parametrize('cid,value', [('CAM-IMG-003',0),('CAM-IMG-003',255),('CAM-IMG-003',128),
    ('CAM-AE-001',20),('CAM-AE-001',240),('CAM-AE-002',0),('CAM-AE-003',255),
    ('CAM-AE-005',0),
    ('CAM-SHP-001',128),('CAM-SHP-002',128),('CAM-SHP-003',128),('CAM-SHP-004',128),
    ('CAM-COLOR-001',0),('CAM-COLOR-002',0),('CAM-SHD-001',0),('CAM-SHD-002',0)])
def test_bad_uniform_frames_fail(cid, value):
    assert not result(cid, np.full((128,128,3),value))


def test_resolution_mismatch():
    assert not result('CAM-IMG-002', texture(), [1920,1080])


def test_exposure_percentiles_detect_clipped_distribution():
    rgb = texture()
    metrics = exposure_percentiles(rgb.astype(float))
    assert metrics["luma_p1"] == pytest.approx(90)
    assert metrics["luma_p99"] == pytest.approx(170)
    rgb[:64] = 0
    assert exposure_percentiles(rgb.astype(float))["luma_p1"] == pytest.approx(0)


def test_exposure_median_is_stable_against_extreme_pixels():
    rgb = texture().astype(float)
    rgb[:8, :8] = 255
    assert exposure_median(rgb)["median_luma"] == pytest.approx(170)


def test_sharpness_heatmap_3x3_detects_local_blur():
    rgb = texture()
    metrics = sharpness_heatmap_3x3(rgb.astype(float))
    assert len(metrics["sharpness_heatmap_3x3"]) == 3
    assert all(len(row) == 3 for row in metrics["sharpness_heatmap_3x3"])
    assert metrics["sharpness_ratio"] >= 0.9


def test_second_wave_proxy_metrics_and_unavailable_inputs(tmp_path):
    rgb = texture().astype(float)
    assert len(grid_metrics(rgb)["luma_grid"]) == 9
    assert noise_metrics(rgb)["signal_to_noise_ratio"] > 0
    assert "lens_distortion" in geometry_metrics(rgb)
    assert compression_metrics(tmp_path / "missing.jpg", rgb)["format"] == ""
    assert sequence_metrics(tmp_path / "missing", rgb)["available"] is False
    assert baseline_metrics(tmp_path / "missing.png", rgb)["available"] is False


def test_siemens_star_mtf_returns_frequency_crossings(tmp_path):
    size = 512
    ys, xs = np.indices((size, size), dtype=float)
    radius = np.hypot(xs - size / 2, ys - size / 2)
    theta = np.arctan2(ys - size / 2, xs - size / 2)
    gray = (128 + 100 * np.cos(18 * theta)).astype(np.uint8)
    gray[radius > 220] = 128
    rgb = np.repeat(gray[:, :, None], 3, axis=2).astype(float)
    blurred = np.asarray(Image.fromarray(rgb.astype(np.uint8)).filter(ImageFilter.GaussianBlur(2)), dtype=float)
    # Deliberately offset the plan anchor; the metric must refine it back to
    # the actual star center before calculating the radial response.
    metrics = siemens_star_mtf(blurred, [{"name": "center", "x": 0.52, "y": 0.48,
                                          "radius": 0.42, "cycles": 18}])
    assert metrics["siemens_star_valid_count"] == 1
    assert metrics["siemens_star_mtf50_cy_px"] > 0
    assert metrics["siemens_star_mtf20_cy_px"] > metrics["siemens_star_mtf50_cy_px"]
    region = metrics["siemens_star_regions"][0]
    assert abs(region["center_px"][0] - size / 2) < 3
    assert abs(region["center_px"][1] - size / 2) < 3
    assert region["center_score"] > 0.2
    assert len(region["roi_bounds_px"]) == 4
    assert {"mtf", "mtf_raw"}.issubset(region["frequency_curve"][0])
    plot_path = Path(plot_siemens_star_mtf(metrics, tmp_path / "mtf.png"))
    assert plot_path.is_file()


def test_chart_localization_rectifies_tilted_plane(tmp_path):
    import cv2

    image = np.full((480, 800, 3), 25, dtype=np.uint8)
    source_quad = np.array([[120, 70], [680, 35], [730, 420], [75, 445]], dtype=np.int32)
    cv2.fillConvexPoly(image, source_quad, (235, 235, 235))
    detection = detect_chart_quad(image.astype(float))
    assert detection["valid"] is True
    rectified = rectify_chart(image.astype(float), canonical_size=(900, 500))
    assert rectified["valid"] is True
    assert rectified["rgb"].shape == (500, 900, 3)
    assert rectified["quad_image_px"][0][0] > 50
    assert Path(save_siemens_star_crops(
        rectified["rgb"],
        {"siemens_star_regions": [{"name": "left", "roi_bounds_px": [100, 100, 180, 180]}]},
        tmp_path,
        "run",
    )["left"]).is_file()


def test_blur_and_single_bad_corner():
    rgb = texture()
    blurred = np.array(Image.fromarray(rgb).filter(ImageFilter.GaussianBlur(4)))
    assert not result('CAM-SHP-001', blurred)
    rgb[:32,:32] = 128
    assert not result('CAM-SHP-003', rgb)
    assert not result('CAM-SHP-004', rgb)


def test_red_cast_and_local_block():
    rgb = np.full((128,128,3),128)
    rgb[:,:,0] = 220
    assert not result('CAM-COLOR-002', rgb)
    rgb = np.full((128,128,3),128)
    rgb[:48,:48] = [255,0,255]
    assert not result('CAM-DEFECT-004', rgb)


def test_shading_single_dark_corner():
    rgb = np.full((128,128,3),128)
    rgb[:32,:32] = 65
    assert not result('CAM-SHD-001', rgb)
    assert not result('CAM-SHD-002', rgb)


def test_decode_unicode_corrupt_and_exif(tmp_path):
    image = tmp_path / '拍摄.png'
    Image.fromarray(texture()).save(image)
    assert decode(image).shape == (128,128,3)
    image.write_bytes(b'broken')
    with pytest.raises(Exception):
        decode(image)
    exif = Image.Exif(); exif[274] = 6
    Image.new('RGB', (64,32)).save(image.with_suffix('.jpg'), exif=exif)
    assert decode(image.with_suffix('.jpg')).shape == (64,32,3)


def test_real_execution_evidence_and_missing_config(tmp_path, monkeypatch):
    monkeypatch.delenv('CAMERA_CONFIG', raising=False)
    # 未设置环境变量时自动发现项目默认 config.json。
    case = case_module('CAM-AE-001')
    path = ROOT / CATALOG['CAM-AE-001']['script_path']
    request = SimpleNamespace(node=SimpleNamespace(obj=case.test_ae_average_brightness, path=path))
    case.test_ae_average_brightness(request, lambda *args: None)
    Image.new('RGB',(128,128)).save(tmp_path/'black.png')
    cfg = tmp_path/'config.json'
    cfg.write_text(json.dumps({'expected_size':[128,128],'images':{'ae':'black.png'}}))
    monkeypatch.setenv('CAMERA_CONFIG',str(cfg))
    monkeypatch.setenv('CAMERA_RESULTS_DIR',str(tmp_path/'evidence'))
    with pytest.raises(AssertionError):
        case.test_ae_average_brightness(request, lambda *args: None)
    evidence=json.loads(next((tmp_path/'evidence').glob('*.json')).read_text(encoding='utf-8'))
    assert evidence['status']=='failed' and evidence['metrics']['mean_luma']==0
    assert evidence['case_id'] == 'CAM-AE-001'
    assert set(evidence['metrics']) == {'mean_luma', 'std_luma', 'under_ratio', 'over_ratio'}


@pytest.mark.parametrize('overrides',[{'under_max':2},{'sharpness_min':float('nan')},{'channel_min':-1}])
def test_invalid_limits(overrides):
    with pytest.raises(ValueError):
        load_limits(ROOT / 'common.json', overrides)


def test_old_global_limits_are_rejected(tmp_path):
    cfg = tmp_path / 'config.json'
    cfg.write_text(json.dumps({'expected_size': [128,128], 'images': {}, 'limits': {'mean_min': 60}}))
    with pytest.raises(ValueError, match='common.json'):
        load_config(cfg)


def test_catalog_unique_complete_and_sync_failure(tmp_path, monkeypatch):
    root=Path(__file__).parents[1]/'testcases'
    cases=collect_cases(root)
    assert len(cases)==60 and len({c['test_class'] for c in cases})==10
    assert all(c['description'] and c['preconditions'] and c['script_path'].startswith('camera/') for c in cases)
    with pytest.raises(ValueError,match='catalog.json'):
        collect_cases(tmp_path)
    def failed(*args, **kwargs):
        raise ConnectionError('offline')
    monkeypatch.setattr('autotest_runner.core.sync.requests.post', failed)
    with pytest.raises(ConnectionError):
        sync_cases(root,'http://localhost:1',None,'project')


def test_junit_case_mapping_uses_metadata_and_legacy_catalog_fallback():
    import xml.etree.ElementTree as ET

    hub_cases = [{"id": "hub-010", "local_case_id": "CAM-SHP-010", "script_path": None}]
    local_cases = [{
        "local_case_id": "CAM-SHP-010",
        "function": "test_sharpness_siemens_star_mtf",
        "script_path": "sharpness/P1/test-sharpness-siemens_star_mtf/test_sharpness_siemens_star_mtf.py",
    }]
    with_property = ET.fromstring(
        '<testcase name="test_sharpness_siemens_star_mtf">'
        '<properties><property name="autotest_case_id" value="CAM-SHP-010"/></properties>'
        '</testcase>'
    )
    assert _resolve_junit_case_id(with_property, hub_cases, local_cases) == "CAM-SHP-010"

    legacy_junit = ET.fromstring(
        '<testcase classname="testcases.camera.sharpness.P1.test-sharpness-siemens_star_mtf" '
        'name="test_sharpness_siemens_star_mtf" '
        'file="testcases\\camera\\sharpness\\P1\\test-sharpness-siemens_star_mtf\\test_sharpness_siemens_star_mtf.py"/>'
    )
    assert _resolve_junit_case_id(legacy_junit, hub_cases, local_cases) == "CAM-SHP-010"


def test_slanted_edge_sfr_matches_gaussian_blur_theory():
    from autotest_runner.camera.sfr import measure_edge

    # 5 度倾斜的暗方块，高斯模糊 sigma=3：理论 MTF50 = 0.1874/sigma。
    size, sigma = 400, 3.0
    ys, xs = np.indices((size * 4, size * 4), dtype=float) / 4.0
    angle = np.radians(5.0)
    u = (xs - 200) * np.cos(angle) + (ys - 200) * np.sin(angle)
    v = -(xs - 200) * np.sin(angle) + (ys - 200) * np.cos(angle)
    square = (np.abs(u) < 120) & (np.abs(v) < 120)
    gray = np.where(square, 30.0, 220.0).reshape(size, 4, size, 4).mean(axis=(1, 3))
    blurred = np.asarray(Image.fromarray(gray.astype(np.uint8)).filter(ImageFilter.GaussianBlur(sigma)), dtype=float)
    rgb = np.repeat(blurred[:, :, None], 3, axis=2)
    # 左边缘：方块局部坐标 u=-120，对应原图两端点。
    p0 = np.array([200 - 120 * np.cos(angle) + 120 * np.sin(angle), 200 - 120 * np.sin(angle) - 120 * np.cos(angle)])
    p1 = np.array([200 - 120 * np.cos(angle) - 120 * np.sin(angle), 200 - 120 * np.sin(angle) + 120 * np.cos(angle)])
    edge = measure_edge(rgb, p0 + [4, 3], p1 + [4, 3], half_width=30)
    assert edge["valid"], edge
    assert edge["mtf50_cy_px"] == pytest.approx(0.1874 / sigma, rel=0.12)
    assert edge["edge_angle_deg"] == pytest.approx(5.0, abs=0.5)


def test_nine_edge_chart_locks_all_patches_and_matches_blur_theory(monkeypatch):
    import cv2
    from autotest_runner.camera import sfr as sfr_module
    from autotest_runner.camera.sfr import find_chart_and_targets, measure_chart_sfr

    card = np.full((1000, 1500, 3), 255, np.uint8)
    for cx in (290, 802, 1328):
        for cy in (177, 469, 756):
            cv2.rectangle(card, (cx - 161, cy - 98), (cx + 66, cy + 98), (0, 0, 0), 3)
            black = np.array([[cx - 56, cy - 98], [cx + 66, cy - 98], [cx + 66, cy + 98], [cx - 76, cy + 98]], np.int32)
            cv2.fillConvexPoly(card, black, (0, 0, 0))
    card = cv2.resize(card, None, fx=2, fy=2, interpolation=cv2.INTER_AREA)
    height, width = card.shape[:2]
    canvas = np.full((int(height * 1.3), int(width * 1.3), 3), 70, np.uint8)
    source = np.float32([[0, 0], [width, 0], [width, height], [0, height]])
    target = np.float32([[260, 220], [width + 230, 170], [width + 290, height + 240], [210, height + 190]])
    photo = cv2.warpPerspective(card, cv2.getPerspectiveTransform(source, target),
                                (canvas.shape[1], canvas.shape[0]), borderValue=(70, 70, 70))
    sigma = 5.0
    photo = cv2.GaussianBlur(photo, (0, 0), sigma).astype(float)
    chart, located, _ = find_chart_and_targets(photo)
    assert chart["valid"] and len(located) == 9
    assert all(item["valid"] for item in located), [item.get("error") for item in located]
    selected_angles = []
    for item in located:
        polygon = np.asarray(item["polygon_canonical"], dtype=float)
        index = item["edge_index"]
        delta = polygon[(index + 1) % len(polygon)] - polygon[index]
        selected_angles.append(np.degrees(np.arctan2(abs(delta[0]), abs(delta[1]))))
    assert all(4.0 <= angle <= 8.0 for angle in selected_angles), selected_angles
    metrics = measure_chart_sfr(photo, chart, located)
    assert metrics["sfr_valid_edge_count"] == 9
    assert metrics["sfr_mtf50_cy_px"] == pytest.approx(0.1874 / sigma, rel=0.15)
    for edge in metrics["sfr_edges"]:
        fitted = np.asarray([edge["fitted_edge_p0_px"], edge["fitted_edge_p1_px"]])
        assert fitted.shape == (2, 2)
        assert all(len(point) == 2 for point in edge["fitted_canonical_segment"])
    angles = [edge["edge_angle_deg"] for edge in metrics["sfr_edges"] if edge["valid"]]
    assert all(4.0 <= angle <= 8.0 for angle in angles), angles

    monkeypatch.setattr(sfr_module, "detect_chart_quad", lambda image: {
        "valid": False, "method": "bright_chart_not_found", "error": "synthetic detector miss",
    })
    fallback_chart, fallback_targets, attempts = find_chart_and_targets(photo)
    assert fallback_chart["method"] == "nine_target_lattice_homography"
    assert fallback_chart["target_lattice_rms_px"] < 8.0
    assert len(fallback_targets) == 9 and all(item["valid"] for item in fallback_targets)
    assert attempts[-1]["method"] == "nine_target_lattice_homography"

    # 白纸没有斜边方块时必须锁定失败而不是给出数值。
    blank = np.full((900, 1400, 3), 70.0)
    blank[100:800, 150:1250] = 235
    blank_chart, blank_located, _ = find_chart_and_targets(blank)
    assert not blank_chart.get("valid") or not blank_located or not all(item["valid"] for item in blank_located)
