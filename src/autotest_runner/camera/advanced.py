"""Shared dispatch for second-wave camera proxy checks."""

from .metrics import (
    baseline_metrics, compression_metrics, defect_detail_metrics, geometry_metrics,
    grid_metrics, noise_metrics, sequence_metrics, sharpness_metrics,
    siemens_star_mtf,
)


def evaluate(kind, run, options=None):
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
    if kind == "siemens_star":
        return siemens_star_mtf(run.rgb, options)
    raise ValueError(f"未知相机代理指标: {kind}")
