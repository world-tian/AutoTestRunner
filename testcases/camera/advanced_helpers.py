"""Thin-case helpers for the second-wave camera proxy checks."""

from autotest_runner.camera.metrics import (
    baseline_metrics, compression_metrics, defect_detail_metrics, geometry_metrics,
    grid_metrics, noise_metrics, sequence_metrics, sharpness_metrics,
)


def evaluate(kind, run):
    if kind == "compression":
        return compression_metrics(run.image_path, run.rgb)
    if kind == "grid":
        return grid_metrics(run.rgb)
    if kind == "noise":
        return noise_metrics(run.rgb)
    if kind == "defect":
        return defect_detail_metrics(run.rgb)
    if kind == "geometry":
        return geometry_metrics(run.rgb)
    if kind == "sequence":
        return sequence_metrics(run.image_path, run.rgb)
    if kind == "baseline":
        return baseline_metrics(run.image_path, run.rgb)
    if kind == "sharpness":
        return sharpness_metrics(run.rgb)
    raise ValueError(f"未知相机代理指标: {kind}")


def metric_reason(ok, text):
    return ok, text