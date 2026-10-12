import base64
import io
import subprocess
import sys
import os
import logging
import json
import re
import shutil
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover - Pillow is a runner dependency
    Image = None

# 尝试加载全局环境变量配置
try:
    from dotenv import load_dotenv
    # 优先加载当前目录的 .env，如果没有则尝试加载家目录下的全局配置
    if os.path.exists(".env"):
        load_dotenv(".env")
    elif os.path.exists(os.path.expanduser("~/.autotest_env")):
        load_dotenv(os.path.expanduser("~/.autotest_env"))
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CLOUD_REQUEST_TIMEOUT = (3, 30)


def _resolve_report_root(workspace):
    """Resolve one stable report root for source-checkout executions.

    The CLI can be launched from the workspace root or from the runner
    project.  Camera evidence, HTML/JUnit output, and runtime artifacts must
    not split across those two current working directories.
    """
    configured = os.getenv("AUTOTEST_REPORTS_ROOT")
    if configured:
        root = Path(configured).expanduser()
        if not root.is_absolute():
            root = Path(workspace) / root
        return root.resolve()

    runner_root = Path(__file__).resolve().parents[3]
    if (runner_root / "src" / "autotest_runner").is_dir() and (runner_root / "testcases").is_dir():
        return (runner_root / "reports").resolve()
    return (Path(workspace) / "reports").resolve()


def _cleanup_camera_bytecode(workspace):
    """删除相机用例运行产生或遗留的 Python 字节码缓存。"""
    workspace_root = Path(workspace)
    camera_roots = [workspace_root / "testcases" / "camera",
                    workspace_root / "autotestrunner" / "testcases" / "camera"]
    for camera_root in camera_roots:
        if not camera_root.is_dir():
            continue
        for cache_dir in camera_root.rglob("__pycache__"):
            if cache_dir.is_dir():
                shutil.rmtree(cache_dir, ignore_errors=True)


def _normalize_case_path(value):
    """将 JUnit 路径和 Hub 的 script_path 统一成可比较的相对路径。"""
    return str(value or "").replace("\\", "/").lstrip("./").lower()


def _load_local_case_catalog(junit_path):
    """读取本地 catalog，给旧 Hub 用例（没有 script_path）提供回退映射。"""
    junit_file = Path(junit_path).resolve()
    candidates = [
        Path.cwd() / "testcases" / "camera" / "catalog.json",
        Path.cwd() / "autotestrunner" / "testcases" / "camera" / "catalog.json",
        Path(__file__).resolve().parents[2] / "testcases" / "camera" / "catalog.json",
        junit_file.parent.parent / "testcases" / "camera" / "catalog.json",
    ]
    for catalog_path in candidates:
        if catalog_path.is_file():
            try:
                entries = json.loads(catalog_path.read_text(encoding="utf-8"))
                return entries if isinstance(entries, list) else []
            except (OSError, ValueError):
                logging.warning("⚠️ 本地 catalog 读取失败: %s", catalog_path)
    return []


def _junit_properties(testcase):
    properties = testcase.find("properties")
    if properties is None:
        return {}
    return {
        prop.get("name"): prop.get("value", "")
        for prop in properties.findall("property")
        if prop.get("name")
    }


def _resolve_junit_case_id(testcase, hub_cases, local_cases=None):
    """用 JUnit 属性、用例函数名和脚本路径将结果映射回 local_case_id。

    旧版 Hub 已同步的用例可能只有 local_case_id，script_path/function 为空；
    因此必须同时保留本地 catalog 作为映射源，不能只依赖 Hub 的扩展字段。
    """
    hub_by_id = {
        item.get("local_case_id"): item
        for item in hub_cases
        if item.get("local_case_id")
    }
    available_ids = set(hub_by_id)
    local_cases = local_cases or []
    properties = _junit_properties(testcase)
    fields = [
        properties.get("autotest_case_id"),
        properties.get("case_id"),
        testcase.get("name", ""),
        testcase.get("classname", ""),
        testcase.get("file", ""),
        properties.get("camera_evidence", ""),
    ]
    text = " ".join(str(value or "") for value in fields)

    # 新版 pytest plugin 会把 case id 写进 JUnit properties；证据文件名也含 case id。
    for case_id in available_ids:
        if case_id and case_id in text:
            return case_id

    function_name = testcase.get("name", "")
    for item in [*hub_cases, *local_cases]:
        if item.get("function") == function_name and item.get("local_case_id") in available_ids:
            return item["local_case_id"]

    junit_file = _normalize_case_path(testcase.get("file", ""))
    if junit_file:
        for item in [*hub_cases, *local_cases]:
            case_id = item.get("local_case_id")
            script_path = _normalize_case_path(item.get("script_path"))
            if case_id in available_ids and script_path and (
                junit_file == script_path or junit_file.endswith("/" + script_path)
            ):
                return case_id

    # 对未规范化的 JUnit/自定义用例保留一个通用的函数名正则回退。
    for item in local_cases:
        case_id = item.get("local_case_id")
        function = item.get("function")
        if case_id in available_ids and function and re.search(rf"(?<![A-Za-z0-9_]){re.escape(function)}(?![A-Za-z0-9_])", text):
            return case_id
    return None


def _read_junit_artifacts(testcase):
    """读取用例证据 JSON，随执行结果传到 Hub 供报告展开查看。"""
    properties = _junit_properties(testcase)
    evidence_path = properties.get("camera_evidence")
    if not evidence_path:
        return None
    path = Path(evidence_path)
    artifacts = {"evidence_path": str(path)}
    try:
        artifacts["evidence"] = json.loads(path.read_text(encoding="utf-8"))
        evidence = artifacts["evidence"]
        images = {}

        def image_paths(value, key):
            if isinstance(value, str):
                if Path(value).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                    yield key, value
                return
            if isinstance(value, dict):
                for child_key, child_value in value.items():
                    child_path = f"{key}.{child_key}" if key else str(child_key)
                    yield from image_paths(child_value, child_path)
                return
            if isinstance(value, list):
                for index, child_value in enumerate(value):
                    yield from image_paths(child_value, f"{key}[{index}]")

        for key, value in image_paths(evidence.get("metrics", {}) or {}, ""):
            image_path = Path(value)
            if not image_path.is_file():
                continue
            image_info = {"path": str(image_path.resolve()), "size_bytes": image_path.stat().st_size}
            try:
                if Image is not None:
                    with Image.open(image_path) as source:
                        image_info["width"], image_info["height"] = source.size
                        preview = source.convert("RGB")
                        # The full-resolution evidence is kept in the local
                        # runtime ZIP.  Hub receives a compact preview so one
                        # result request stays below common reverse-proxy body
                        # limits while still rendering the analyzed regions.
                        preview.thumbnail((640, 400))
                        buffer = io.BytesIO()
                        preview.save(buffer, format="JPEG", quality=68, optimize=True)
                        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
                        image_info["preview_data_url"] = f"data:image/jpeg;base64,{encoded}"
                        image_info["preview_width"], image_info["preview_height"] = preview.size
            except (OSError, ValueError):
                image_info["preview_readable"] = False
            images[key] = image_info
        if images:
            artifacts["images"] = images
    except (OSError, ValueError):
        artifacts["evidence_readable"] = False
    return artifacts


def _publish_report(hub_url, token, plan_config, report_name, returncode, duration_sec):
    """将本地执行结果登记到 Hub 的 CI Reports 页面。HTML 仍保留本地路径供审计。"""
    if not hub_url:
        return
    plan_name = (plan_config or {}).get("name") or "AutoTestRunner 本地测试"
    payload = {
        "name": plan_name,
        "status": "success" if returncode == 0 else "failed",
        "source": "autotestrunner",
        "trigger_name": "local-runner",
        "duration": int(duration_sec * 1000),
        "pipeline_url": str(Path(report_name).resolve()),
        "jobs": [{
            "name": plan_name,
            "stage": "camera" if "camera" in plan_name.lower() else "local",
            "status": "success" if returncode == 0 else "failed",
            "duration": int(duration_sec * 1000),
            "web_url": str(Path(report_name).resolve()),
        }],
    }
    try:
        response = requests.post(
            f"{hub_url.rstrip('/')}/api/ci-reports",
            headers={"Authorization": f"Bearer {token}"} if token else {},
            json=payload,
            timeout=CLOUD_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        logging.info("☁️ AutoTestHub 报告已同步: %s", response.json().get("id", ""))
    except Exception as exc:
        logging.error("❌ AutoTestHub 报告同步失败: %s", exc)


def _publish_execution_run(hub_url, token, project_id, plan_config, returncode, junit_path, execution_log=""):
    """登记到 Hub 的测试执行报告（与 CI 报告分离）。"""
    if not (hub_url and project_id):
        return
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    name = (plan_config or {}).get("name") or "AutoTestRunner 本地执行"
    run_id = None
    try:
        response = requests.post(f"{hub_url.rstrip('/')}/api/projects/{project_id}/execution-runs",
                                 headers=headers, json={"name": name}, timeout=CLOUD_REQUEST_TIMEOUT)
        response.raise_for_status()
        run_id = response.json()["id"]
        cases_response = requests.get(f"{hub_url.rstrip('/')}/api/projects/{project_id}/test-cases", headers=headers, timeout=CLOUD_REQUEST_TIMEOUT)
        cases_response.raise_for_status()
        cases = cases_response.json()
        local_cases = _load_local_case_catalog(junit_path)
        root = ET.parse(junit_path).getroot()
        junit_cases = list(root.iter("testcase"))
        matched = 0
        unmatched = []
        for testcase in junit_cases:
            case_id = _resolve_junit_case_id(testcase, cases, local_cases)
            hub_case = next((item for item in cases if item.get("local_case_id") == case_id), None)
            if not hub_case or not hub_case.get("id"):
                unmatched.append(testcase.get("name", "<unnamed>"))
                continue
            failure = testcase.find("failure")
            skipped = testcase.find("skipped")
            status = "failed" if failure is not None else "skipped" if skipped is not None else "passed"
            duration_ms = None
            if testcase.get("time"):
                try:
                    duration_ms = round(float(testcase.get("time")) * 1000)
                except (TypeError, ValueError):
                    pass
            payload = {
                "test_case_id": hub_case["id"],
                "status": status,
                "error_message": (failure.text if failure is not None else None),
                "log_url": execution_log[-20000:] if execution_log else None,
                "duration_ms": duration_ms,
                "artifacts": _read_junit_artifacts(testcase),
            }
            requests.post(f"{hub_url.rstrip('/')}/api/execution-runs/{run_id}/results", headers=headers,
                          json=payload, timeout=CLOUD_REQUEST_TIMEOUT).raise_for_status()
            matched += 1
        if unmatched:
            logging.warning("⚠️ AutoTestHub 有 %d 条 JUnit 用例未关联: %s", len(unmatched), ", ".join(unmatched))
        if junit_cases and matched == 0:
            raise RuntimeError("JUnit 中没有任何用例成功映射到 AutoTestHub；已阻止生成空执行报告")
        status = "completed" if returncode == 0 else "failed"
        requests.patch(f"{hub_url.rstrip('/')}/api/execution-runs/{run_id}/status",
                       headers=headers, params={"status": status}, timeout=CLOUD_REQUEST_TIMEOUT).raise_for_status()
        logging.info("☁️ AutoTestHub 测试执行报告已同步: %s（%d/%d 条用例）", run_id, matched, len(junit_cases))
    except Exception as exc:
        if run_id:
            try:
                requests.patch(f"{hub_url.rstrip('/')}/api/execution-runs/{run_id}/status",
                               headers=headers, params={"status": "failed"}, timeout=CLOUD_REQUEST_TIMEOUT).raise_for_status()
            except Exception as status_exc:
                logging.error("❌ AutoTestHub 执行报告状态回写失败: %s", status_exc)
        logging.error("❌ AutoTestHub 测试执行报告同步失败: %s", exc)


def _run_pytest_process(pytest_args, cwd, env):
    """Run pytest while retaining the same live console output for cloud logs."""
    process = subprocess.Popen(
        pytest_args,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    output = []
    assert process.stdout is not None
    for line in process.stdout:
        output.append(line)
        print(line, end="", flush=True)
    returncode = process.wait()
    return returncode, "".join(output)


def _resolve_target(path, launch_dir):
    """允许从工作区根目录执行：自动映射到 autotestrunner 子项目。"""
    candidate = Path(path)
    if candidate.is_absolute() and candidate.exists():
        return str(candidate)
    direct = Path(launch_dir) / candidate
    if direct.exists():
        return str(direct)
    runner_root = Path(__file__).resolve().parents[3]
    nested = runner_root / candidate
    if nested.exists():
        logging.info("📍 自动定位 Runner 目标: %s -> %s", path, nested)
        return str(nested)
    return str(direct)

def run_tests_locally(target_paths, report_to_cloud=False, hub_url=None, token=None, plan_config=None, allow_failures=False):
    if isinstance(target_paths, str):
        target_paths = [target_paths]
        
    logging.info(f"🚀 本地执行目标: {target_paths}")
    
    # 从全局环境变量获取工作目录，如果未配置则使用当前绝对路径
    global_workspace = os.getenv("AUTOTEST_WORKSPACE")
    if global_workspace and os.path.exists(global_workspace):
        abs_cwd = os.path.abspath(global_workspace)
        logging.info(f"📁 使用全局配置的工作目录: {abs_cwd}")
    else:
        abs_cwd = os.path.abspath(os.getcwd())
        logging.info(f"📁 使用当前工作目录: {abs_cwd}")

    target_paths = [_resolve_target(path, abs_cwd) for path in target_paths]
        
    exec_source = os.getenv("AUTOTEST_SOURCE", "local")
    reports_root = _resolve_report_root(abs_cwd)
    reports_dir = str(reports_root / exec_source)
    logging.info(f"📦 报告根目录: {reports_root}")
    
    # 彻底解决 MacOS Sandbox/SIP 导致的 Operation not permitted 权限问题
    test_file = os.path.join(reports_dir, ".test_write")
    started_at = datetime.now()
    try:
        os.makedirs(reports_dir, exist_ok=True)
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
    except Exception as e:
        logging.warning(f"⚠️ 当前目录无写入权限 ({e})，报告将重定向至 /tmp/autotest_reports/{exec_source}")
        reports_root = Path(f"/tmp/autotest_reports")
        reports_dir = str(reports_root / exec_source)
        os.makedirs(reports_dir, exist_ok=True)
        
    report_name = os.path.join(reports_dir, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
    junit_name = os.path.join(reports_dir, f"junit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml")

    # 即使不使用 plan 也加载插件，以便 HTML 报告显示中文描述和编号。
    runtime_plan_arg = ["-p", "autotest_runner.pytest_plugin"]
    if plan_config:
        plan_snapshot = Path(reports_dir) / "runtime_plan.json"
        plan_snapshot.write_text(json.dumps(plan_config, ensure_ascii=False, indent=2), encoding="utf-8")
        runtime_plan_arg.append(f"--autotest-plan-config={plan_snapshot}")
    
    # 改为使用 python -m pytest 直接在指定目录下启动，满足用户的习惯
    # -s 保留每条相机用例的“开始/指标/判定”打印，便于现场观察。
    # 相机用例目录保持纯源码：禁止 Python 为测试脚本写入 __pycache__。
    # 这是环境变量而不是测试代码开关，因此子进程导入阶段也生效。
    child_env = os.environ.copy()
    child_env["PYTHONDONTWRITEBYTECODE"] = "1"
    child_env["PYTHONIOENCODING"] = "utf-8"
    child_env["AUTOTEST_REPORTS_ROOT"] = str(reports_root)
    child_env["CAMERA_RESULTS_DIR"] = str(reports_root / "camera")
    pytest_args = [sys.executable, "-m", "pytest"] + target_paths + runtime_plan_arg + ["-v", "-s", f"--html={report_name}", "--self-contained-html", f"--junitxml={junit_name}", "-p", "no:cacheprovider"]
    
    try:
        logging.info(f"⚙️ 拉起子进程执行命令: {' '.join(pytest_args)}")
        returncode, execution_log = _run_pytest_process(pytest_args, cwd=abs_cwd, env=child_env)
        logging.info(f"📊 本地报告已生成: {report_name}")
        if report_to_cloud:
            _publish_execution_run(hub_url, token, os.getenv("AUTOTEST_PROJECT_ID"), plan_config, returncode, junit_name, execution_log)
        if returncode != 0 and allow_failures:
            logging.warning("⚠️ 测试报告包含失败用例；已按 --allow-failures 返回成功，详见 HTML/JUnit 报告")
            return 0
        return returncode
    except Exception as e:
        logging.error(f"❌ pytest 执行过程中发生异常: {e}")
        return 1
    finally:
        _cleanup_camera_bytecode(abs_cwd)
