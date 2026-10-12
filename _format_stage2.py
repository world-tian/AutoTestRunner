from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).parent / "testcases" / "camera"
TARGETS = [
    ("output", ["test-output-duplicate_frame", "test-output-jpeg_compression"]),
    ("sharpness", ["test-sharpness-mtf50", "test-sharpness-mtf20", "test-sharpness-corner_center_mtf_ratio"]),
    ("awb", ["test-awb-colorchecker_delta_e"]),
    ("shading", ["test-shading-luma_9x9_heatmap", "test-shading-color_9x9_heatmap"]),
    ("noise", ["test-noise-luma_noise", "test-noise-dark_frame_noise", "test-noise-chroma_noise", "test-noise-signal_to_noise_ratio", "test-noise-temporal_noise"]),
    ("geometry", ["test-geometry-lens_distortion", "test-geometry-lateral_chromatic_aberration", "test-geometry-optical_center_offset", "test-geometry-perspective_error"]),
    ("defect", ["test-defect-hot_pixel", "test-defect-dead_pixel", "test-defect-horizontal_banding", "test-defect-vertical_banding", "test-defect-frame_corruption", "test-defect-duplicate_frame"]),
    ("underwater", ["test-underwater-sharpness_change", "test-underwater-fov_distortion", "test-underwater-contrast_loss", "test-underwater-awb", "test-underwater-backscatter"]),
    ("regression", ["test-regression-firmware_metrics", "test-regression-isp_metrics", "test-regression-golden_sample"]),
]

MISSING = {
    "test_noise_luma_noise": ("CAM-NOISE-001", "亮度噪声", "luma_noise", ("luma_noise", "mean_luma"), 'metrics["luma_noise"] <= limits["luma_noise_max"]', 'f"亮度噪声={metrics[\'luma_noise\']:.3f}"', 'evaluate("luma", run)'),
    "test_noise_dark_frame_noise": ("CAM-NOISE-004", "暗场噪声", "dark", ("mean_luma", "luma_noise"), 'metrics["mean_luma"] <= limits["dark_mean_max"] and metrics["luma_noise"] <= limits["dark_noise_max"]', 'f"暗场均值={metrics[\'mean_luma\']:.3f}，噪声={metrics[\'luma_noise\']:.3f}"', 'evaluate("dark", run)'),
    "test_noise_chroma_noise": ("CAM-NOISE-002", "色度噪声", "chroma", ("chroma_noise",), 'metrics["chroma_noise"] <= limits["chroma_noise_max"]', 'f"色度噪声={metrics[\'chroma_noise\']:.3f}"', 'evaluate("chroma", run)'),
    "test_noise_signal_to_noise_ratio": ("CAM-NOISE-003", "信噪比", "snr", ("signal_to_noise_ratio", "snr_db"), 'metrics["signal_to_noise_ratio"] >= limits["snr_min"] and metrics["snr_db"] >= limits["snr_db_min"]', 'f"SNR={metrics[\'signal_to_noise_ratio\']:.3f}，SNR(dB)={metrics[\'snr_db\']:.3f}"', 'evaluate("snr", run)'),
    "test_noise_temporal_noise": ("CAM-NOISE-005", "时域噪声", "sequence", ("available", "frame_count", "temporal_noise"), 'metrics["available"] and metrics["temporal_noise"] <= limits["temporal_noise_max"]', '"需要至少两帧" if not metrics["available"] else f"帧数={metrics[\'frame_count\']}，时域噪声={metrics[\'temporal_noise\']:.3f}"', 'evaluate("sequence", run)'),
    "test_geometry_lateral_chromatic_aberration": ("CAM-GEO-002", "横向色差LCA", "geometry", ("lateral_chromatic_aberration",), 'metrics["lateral_chromatic_aberration"] <= limits["lca_max"]', 'f"横向色差代理={metrics[\'lateral_chromatic_aberration\']:.3f}"', 'evaluate("geometry", run)'),
}


def literal(node):
    return ast.literal_eval(node)


def format_file(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    assignments = {n.targets[0].id: n.value for n in tree.body if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)}
    test_node = next((n for n in functions.values() if n.name.startswith("test_")), None)
    key = test_node.name if test_node else path.stem
    missing = MISSING.get(key)
    if missing:
        case_id, title, mode, metric_keys, expression, reason, metrics_expr = missing
        description = f"使用{title}代理指标检查真实输入；连续帧或输入条件不足时按N/A处理，不伪造PASS。"
        expected = f"{title}代理指标满足CASE_LIMITS；正式产品验收需标定输入，条件不具备时记录N/A。"
        function_name = key
        check_lines = [f"    ok = {expression}", f"    reason = {reason}", "    return ok, reason"]
    else:
        decorator = test_node.decorator_list[0].keywords if test_node and test_node.decorator_list and isinstance(test_node.decorator_list[0], ast.Call) else []
        values = {k.arg: literal(k.value) for k in decorator if k.arg in {"case_id", "title", "description", "expected_result"}}
        case_id = values.get("case_id", "")
        title = values.get("title", key)
        description = values.get("description", "")
        expected = values.get("expected_result", "")
        function_name = test_node.name if test_node else key
        check_node = functions.get("check")
        statements = [] if check_node is None else [n for n in check_node.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str))]
        check_lines = [f"    {line}" for n in statements for line in ast.unparse(n).splitlines()]
        metrics_expr = 'evaluate("default", run)'
        if test_node:
            for n in ast.walk(test_node):
                if isinstance(n, ast.Assign) and n.targets and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "metrics":
                    metrics_expr = ast.unparse(n.value)
                    break
        metric_node = assignments.get("METRIC_KEYS", ast.Tuple(elts=[]))
        metric_keys = tuple(literal(n) for n in metric_node.elts)
    limits = assignments.get("CASE_LIMITS", ast.Dict(keys=[], values=[]))
    limit_lines = [f'    "{literal(k)}": {ast.unparse(v)},  # {literal(k)} 的本用例阈值。' for k, v in zip(limits.keys, limits.values)]
    metric_lines = [f'    "{item}",  # 记录{item}，用于本用例的判定或证据。' for item in metric_keys]
    if "color_metrics" in path.read_text(encoding="utf-8"):
        metric_import = "from autotest_runner.camera.metrics import color_metrics"
    elif "image_size" in path.read_text(encoding="utf-8"):
        metric_import = "from autotest_runner.camera.metrics import image_size"
    else:
        metric_import = "from autotest_runner.camera.advanced import evaluate"
    if "N/A" not in description:
        description += " 输入限制不满足时记录N/A，当前实现为代理算法。"
    if "N/A" not in expected:
        expected += " 仅代表代理检查；缺少规定输入时必须记录N/A。"
    header = f'''"""{case_id}：{title}\n测试大类：{path.parts[-3]} / Camera IQ。\n目的：验证{title}并输出可复核的代理指标。\n前置条件：使用真实图片；连续帧、标定卡或基线不可用时记录N/A，不伪造PASS。\n判定标准：按check中的关键指标与CASE_LIMITS逐项比较，必要条件全部满足才通过。\n图片来源：camera_case按--picture优先，其次读取配置中的images.output，最后使用images.default。\n阈值来源：CASE_LIMITS逐项定义；共享阈值来自common.json，专用项来自本文件，代理限制仅作基础筛查。\n"""'''
    check_doc = '''    """说明本用例的输入、输出、关键指标和阈值判定。\n\n    输入为指标字典、已合并阈值和期望尺寸；输出为通过标志及中文原因。\n    关键指标由METRIC_KEYS声明，check只执行本用例代理判定，不负责生成指标。\n    任一关键指标超出CASE_LIMITS或前置条件不满足时返回False；不适用输入保留N/A语义。\n    """'''
    body = f'''{header}\n\nfrom autotest_runner import autotest\n\n{metric_import}\n\nfrom autotest_runner.camera.execution import camera_case\n\nCASE_LIMITS = {{\n{chr(10).join(limit_lines)}\n}}\n\nMETRIC_KEYS = (\n{chr(10).join(metric_lines)}\n)\n\ndef check(metrics, limits, expected_size):\n{check_doc}\n{chr(10).join(check_lines)}\n\n@autotest(\n    case_id={case_id!r},\n    title={title!r},\n    priority="P1",\n    test_class={f"{path.parts[-3]} / Camera IQ"!r},\n    description={description!r},\n    expected_result={expected!r},\n    parameters=CASE_LIMITS,\n)\ndef {function_name}(request, record_property):\n    """按准备、指标、判定、记录、失败抛异常五步执行本用例。"""\n    # 1. 公共准备读取真实图片、输入限制和生效阈值。\n    with camera_case(request, record_property, CASE_LIMITS) as run:\n        # 2. 调用已有公共代理算法计算指标。\n        metrics = {metrics_expr}\n        # 3. 调用本脚本判定逻辑比较关键指标和阈值。\n        ok, reason = check(metrics, run.limits, run.expected_size)\n        # 4. 保存指标、判定和证据，供报告复核。\n        run.record(metrics, ok, reason, METRIC_KEYS)\n        # 5. 失败时显式抛出异常，不吞掉判定结果。\n        if not ok:\n            raise AssertionError(f"{{run.case_id}}: {{reason}}")\n'''
    path.write_text(body, encoding="utf-8")


for domain, names in TARGETS:
    for name in names:
        matches = list((ROOT / domain / "P1" / name).glob("test_*.py"))
        if len(matches) != 1:
            raise RuntimeError(f"target not unique: {domain}/{name}: {matches}")
        format_file(matches[0])