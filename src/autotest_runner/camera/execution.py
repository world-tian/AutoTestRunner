"""相机公共准备与证据保存；业务指标和断言写在各自用例中。"""
import json
import math
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from .metrics import decode

COMMON_KEYS = {"mean_min", "sharpness_min", "channel_min"}
RATIO_KEYS = {"under_max", "over_max", "extreme_max", "sharpness_ratio_min"}


def load_config(path):
    path = Path(path).resolve()
    config = json.loads(path.read_text(encoding="utf-8"))
    if "limits" in config:
        raise ValueError("config.json 不再存放阈值；通用项请配置 common.json，专用项请配置各用例 CASE_LIMITS")
    size = config.get("expected_size")
    if not isinstance(size, list) or len(size) != 2 or any(type(v) is not int or v < 32 for v in size):
        raise ValueError("expected_size 必须填写实际规格 [宽, 高]，各项至少为32")
    if not isinstance(config.get("images"), dict):
        raise ValueError("images 必须按 output/ae/sharpness/awb/shading/defect 配置图片")
    return path, config


def load_limits(common_path, case_limits):
    """合并通用和用例专用阈值，拒绝重复/无效值。"""
    common = json.loads(Path(common_path).read_text(encoding="utf-8"))
    if not isinstance(common, dict) or set(common) != COMMON_KEYS:
        raise ValueError(f"common.json 必须包含通用阈值: {sorted(COMMON_KEYS)}")
    if set(case_limits) & COMMON_KEYS:
        raise ValueError("用例专用阈值不能覆盖 common.json 通用项")
    limits = {**common, **case_limits}
    for key, value in limits.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f"无效阈值 {key}: {value}")
        if key in RATIO_KEYS and value > 1:
            raise ValueError(f"比例阈值 {key} 必须在 0..1")
    return limits


class CameraCase:
    """只保存运行上下文与证据；不选择算法，也不决定 PASS/FAIL。"""

    def __init__(self, case_id, category, image_path, config_path, common_path,
                 limits, expected_size, artifact, record_property):
        self.case_id = case_id
        self.category = category
        self.image_path = image_path
        self.limits = limits
        self.expected_size = expected_size
        self.artifact = artifact
        self.record_property = record_property
        self.evidence = {
            "case_id": case_id, "category": category, "image": str(image_path),
            "config": str(config_path), "common_config": str(common_path),
            "limits": limits, "expected_size": expected_size,
        }
        self.rgb = None

    def record(self, metrics, ok, reason, metric_keys):
        """保存本用例指标与中文判定；失败异常由脚本显式抛出。"""
        self.evidence.update(metrics=metrics, status="passed" if ok else "failed", assertion=reason)
        summary = {key: metrics[key] for key in metric_keys if key in metrics}
        print(f"[CAMERA] {self.case_id} 实测指标: {json.dumps(summary, ensure_ascii=False)}", flush=True)
        print(f"[CAMERA] {self.case_id} {'PASS' if ok else 'FAIL'} | {reason}", flush=True)

    def save(self, error=None):
        if error is not None:
            self.evidence.update(status="failed", error=str(error))
        self.artifact.write_text(json.dumps(self.evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        self.record_property("camera_evidence", str(self.artifact.resolve()))
        print(f"[CAMERA] {self.case_id} 结果证据: {self.artifact}", flush=True)


@contextmanager
def camera_case(request, record_property, case_limits=None):
    """从 pytest 用例元数据获取编号；准备真实图片，退出时始终保存证据。"""
    meta = getattr(request.node.obj, "__autotest_meta__", {}) or {}
    case_id = meta.get("case_id")
    if not case_id:
        raise ValueError("相机用例必须用 @autotest 声明 case_id")
    test_path = Path(str(request.node.path)).resolve()
    category = ""
    for parent in test_path.parents:
        if parent.name == "camera" and parent.parent.name == "testcases":
            category = test_path.relative_to(parent).parts[0]
            break
    if not category:
        raise ValueError(f"相机用例路径必须位于 testcases/camera/<模块> 下: {test_path}")
    runner_root = Path(__file__).resolve().parents[3]
    config_path = os.getenv("CAMERA_CONFIG")
    if not config_path:
        candidates = [Path.cwd() / "testcases/camera/config.json",
                      runner_root / "testcases/camera/config.json"]
        config_path = next((str(candidate) for candidate in candidates if candidate.is_file()), None)
    if not config_path:
        raise ValueError("未找到相机配置；请设置 CAMERA_CONFIG 指向 config.json")
    path, config = load_config(config_path)
    common_path = path.parent / "common.json"
    if not common_path.is_file():
        common_path = Path(__file__).resolve().parents[3] / "testcases/camera/common.json"
    limits = load_limits(common_path, case_limits or {})
    image = os.getenv("CAMERA_PICTURE") or config["images"].get(category) or config["images"].get("default")
    if not image:
        raise ValueError(f"请配置 images.{category} 的真实拍摄图片")
    image_path = Path(image)
    if not image_path.is_absolute():
        relative_candidates = (
            (Path.cwd() / image_path).resolve(),
            (runner_root / image_path).resolve(),
            (path.parent / image_path).resolve(),
        )
        image_path = next((candidate for candidate in relative_candidates if candidate.exists()), relative_candidates[-1])
    if image_path.is_dir():
        candidates = sorted(p for p in image_path.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"})
        if not candidates:
            raise ValueError(f"图片目录没有 JPG/PNG 等图片: {image_path}")
        image_path = next((p for p in candidates if p.stem.lower() == category.lower()), candidates[0]).resolve()
    output = Path(os.getenv("CAMERA_RESULTS_DIR", "reports/camera"))
    output.mkdir(parents=True, exist_ok=True)
    artifact = output / f"{case_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
    case = CameraCase(case_id, category, image_path, path, common_path,
                      limits, config["expected_size"], artifact, record_property)
    print(f"[CAMERA] 开始执行 {case_id} | 测试大类={category} | 图片={image_path}", flush=True)
    try:
        case.rgb = decode(image_path)
        yield case
    except Exception as exc:
        case.save(exc)
        raise
    else:
        case.save()
