import json
import logging
import os
from pathlib import Path

import pytest

from autotest_runner.runtime import RuntimeManager

logger = logging.getLogger(__name__)
_plan_name = "本地测试计划"
_plan_order = {}
_plan_case_ids = None
_global_priority = "P0"


def _case_meta(item):
    meta = getattr(getattr(item, "obj", None), "__autotest_meta__", {}) or {}
    return meta


def _module_name(meta):
    """模块来自脚本 feature（通常是 testcases 下的一级目录），不写死在 plan。"""
    feature = meta.get("feature") or ""
    parts = [part for part in str(feature).replace("\\", "/").split("/") if part]
    return parts[-1] if parts else (meta.get("test_class") or "-")


def pytest_html_results_table_header(cells):
    """pytest-html 报告增加中文说明列，避免只显示 Python 函数名。"""
    cells.insert(1, '<th class="sortable col-description">中文用例描述</th>')
    cells.insert(2, '<th class="sortable col-case_id">用例编号</th>')
    cells.insert(3, '<th class="sortable col-module">模块</th>')
    cells.insert(4, '<th class="sortable col-priority">优先级</th>')
    cells[:] = [cells[2], cells[3], cells[4], cells[5], cells[1], cells[6], cells[0], cells[7]]


def pytest_html_report_title(report):
    report.title = f"{_plan_name} · AutoTestRunner 测试报告"


def pytest_html_results_summary(prefix, summary, postfix, session):
    """注入单文件报告样式，改善状态、层次和中文阅读体验。"""
    prefix.extend(['''<style>
:root{--ink:#101828;--muted:#344054;--line:#d0d5dd;--brand:#4338ca;--bg:#f3f6fb}body{background:var(--bg);color:var(--ink);font-family:Inter,"PingFang SC","Microsoft YaHei",Arial,sans-serif;max-width:1500px;margin:0 auto;padding:30px 38px;font-size:15px}h1{font-size:30px;letter-spacing:-.02em;margin:0 0 6px;color:#101828}h2{font-size:18px;margin:28px 0 12px;color:#101828}table{width:100%;border:1px solid #d0d5dd;border-collapse:separate;border-spacing:0;background:#fff;color:#101828;border-radius:14px;overflow:hidden;box-shadow:0 8px 24px #10182814}th{background:#eef2ff!important;color:#1e1b4b!important;font-size:14px;font-weight:700;padding:15px 16px!important;border-bottom:2px solid #c7d2fe!important;white-space:nowrap}td{padding:16px!important;border-bottom:1px solid var(--line)!important;vertical-align:top;font-size:15px;line-height:1.6;color:#101828!important}tr:last-child td{border-bottom:0!important}tr:has(.result-passed) td{background:#f0fdf4!important}tr:has(.result-failed) td{background:#fff1f0!important}tr:has(.result-skipped) td{background:#fffaeb!important}tr:has(.result-passed) .col-case_id{color:#067647!important;font-weight:800;border-left:4px solid #12b76a}tr:has(.result-failed) .col-case_id{color:#b42318!important;font-weight:800;border-left:4px solid #f04438}tr:has(.result-skipped) .col-case_id{color:#b54708!important;font-weight:800;border-left:4px solid #f79009}th.col-description{width:28%}th.col-case_id{width:13%}th.col-module{width:18%}th.col-priority{width:8%}th.col-testId,td.col-testId{max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--muted)!important;font-size:13px}.logwrapper{background:#fff!important;border:1px solid var(--line);border-radius:10px;margin:10px 0!important}.logwrapper pre{font-family:Consolas,monospace;font-size:13px;white-space:pre-wrap;color:#344054}#environment{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 18px;box-shadow:0 8px 24px #10182814}#environment table{box-shadow:none}button{border:0!important;border-radius:999px!important;background:#e4e7ec!important;color:#344054!important;font-weight:700;padding:8px 16px!important;margin:8px 4px 0 0;cursor:pointer;box-shadow:0 2px 5px #1018281a}button[data-filter="Passed"]{background:#d1fadf!important;color:#067647!important}button[data-filter="Failed"]{background:#fee4e2!important;color:#b42318!important}button[data-filter="Skipped"]{background:#fef0c7!important;color:#b54708!important}button[data-filter^="P"]{background:#e0e7ff!important;color:#3730a3!important}button:hover,button:focus{outline:3px solid #c7d2fe!important}input[type=checkbox]{accent-color:var(--brand)}.report-intro{font-size:15px!important}
</style>''',f'<div class="report-intro"><strong>CAMERA QUALITY / 自动化质量报告</strong><br><span>{_plan_name} · 报告结果　｜　中文描述、判定参数与关键实测值按用例元数据展示</span><br><button data-filter="all">全部</button> <button data-filter="Passed">PASS</button> <button data-filter="Failed">FAIL</button> <button data-filter="Skipped">SKIP</button> <button data-filter="P0">P0</button> <button data-filter="P1">P1</button> <button data-filter="P2">P2</button> <button data-filter="P3">P3</button></div>', '''<script>
document.addEventListener('click',function(e){var b=e.target.closest('[data-filter]');if(!b)return;var f=b.dataset.filter;document.querySelectorAll('table tbody tr').forEach(function(r){var result=r.querySelector('.col-result'),priority=r.querySelector('.col-priority');var text=(result?result.textContent:'')+' '+(priority?priority.textContent:'');r.style.display=(!result||f==='all'||text.indexOf(f)>=0)?'':'none'});document.querySelectorAll('[data-filter]').forEach(function(x){x.style.opacity=x===b?'1':'.72'})});
</script>'''])


def pytest_html_results_table_row(report, cells):
    meta = getattr(report, "_autotest_meta", {}) or {}
    import html
    text = meta.get("description") or meta.get("title") or "-"
    cells.insert(1, f'<td class="col-description">{html.escape(text)}</td>')
    cells.insert(2, f'<td class="col-case_id">{html.escape(meta.get("case_id") or "-")}</td>')
    cells.insert(3, f'<td class="col-module">{html.escape(_module_name(meta))}</td>')
    cells.insert(4, f'<td class="col-priority">{html.escape(meta.get("priority") or _global_priority)}</td>')
    result_class = {"passed": "result-passed", "failed": "result-failed", "skipped": "result-skipped"}.get(report.outcome, "")
    cells[0] = cells[0].replace('class="col-result"', f'class="col-result {result_class}"')
    if result_class:
        # 直接给整行单元格写入背景色，兼容不支持 CSS :has() 的报告查看器。
        row_style = {"result-passed": "background:#f0fdf4!important;",
                     "result-failed": "background:#fff1f0!important;",
                     "result-skipped": "background:#fffaeb!important;"}[result_class]
        cells[:] = [cell.replace('class="', f'class="{result_class} ', 1).replace('<td ', f'<td style="{row_style}" ', 1) if '<td ' in cell else cell for cell in cells]
    cells[:] = [cells[2], cells[3], cells[4], cells[5], cells[1], cells[6], cells[0], cells[7]]


def pytest_runtest_logreport(report):
    # 将元数据挂到 pytest-html 的 report 对象，表格行钩子可读取。
    item = getattr(report, "item", None)
    if item is not None:
        report._autotest_meta = _case_meta(item)


def pytest_addoption(parser):
    group = parser.getgroup("autotest-runner")
    group.addoption(
        "--autotest-plan-config",
        action="store",
        default=None,
        help="AutoTestRunner runtime plan JSON file.",
    )


def pytest_configure(config):
    global _plan_name, _plan_order, _plan_case_ids, _global_priority
    plan_path = config.getoption("--autotest-plan-config") or os.getenv("AUTOTEST_PLAN_CONFIG")
    if not plan_path:
        config.autotest_runtime = None
        return

    with open(plan_path, "r", encoding="utf-8") as plan_file:
        plan = json.load(plan_file)
    _plan_name = plan.get("name") or "本地测试计划"
    camera_config = os.getenv("CAMERA_CONFIG")
    if camera_config and Path(camera_config).is_file():
        try:
            camera_data = json.loads(Path(camera_config).read_text(encoding="utf-8"))
            _global_priority = camera_data.get("priority", {}).get("default", "P0")
        except (ValueError, OSError):
            pass
    catalog = plan.get("case_catalog")
    explicit_cases = plan.get("cases") or []
    _plan_case_ids = set(explicit_cases) if explicit_cases else None
    if explicit_cases:
        _plan_order = {case_id: index for index, case_id in enumerate(explicit_cases)}
    if catalog:
        catalog_path = Path(plan_path).resolve().parent.parent / catalog
        if not catalog_path.is_file():
            catalog_path = Path(os.getcwd()) / catalog
        if not catalog_path.is_file():
            catalog_path = Path(__file__).resolve().parents[2] / catalog
        if catalog_path.is_file():
            try:
                entries = json.loads(catalog_path.read_text(encoding="utf-8"))
                if not explicit_cases:
                    _plan_order = {entry.get("local_case_id"): index for index, entry in enumerate(entries)}
            except (ValueError, OSError):
                _plan_order = {}

    reports_root = os.getenv("AUTOTEST_REPORTS_ROOT")
    runtime_base = Path(reports_root).resolve().parent if reports_root else Path.cwd()
    runtime = RuntimeManager(plan, base_dir=runtime_base)
    runtime.start_session()
    config.autotest_runtime = runtime


def pytest_collection_modifyitems(config, items):
    """按 plan cases 筛选并按定义顺序排列，避免误跑整个 target 目录。"""
    if _plan_case_ids is not None:
        selected, deselected = [], []
        for item in items:
            if _case_meta(item).get("case_id") in _plan_case_ids:
                selected.append(item)
            else:
                deselected.append(item)
        items[:] = selected
        if deselected:
            config.hook.pytest_deselected(items=deselected)
    if not _plan_order:
        return
    items.sort(key=lambda item: _plan_order.get(_case_meta(item).get("case_id"), len(_plan_order)))


def pytest_sessionfinish(session, exitstatus):
    runtime = getattr(session.config, "autotest_runtime", None)
    if runtime:
        runtime.finish_session()


@pytest.fixture
def serial(request):
    runtime = getattr(request.config, "autotest_runtime", None)
    if not runtime or not runtime.serial_tool:
        pytest.skip("Serial is not enabled in AutoTestRunner plan")
    return runtime.serial_tool


@pytest.fixture
def adb(request):
    runtime = getattr(request.config, "autotest_runtime", None)
    if not runtime or not runtime.adb_tool:
        pytest.skip("ADB is not enabled in AutoTestRunner plan")
    return runtime.adb_tool


def pytest_runtest_setup(item):
    item._autotest_meta = _case_meta(item)
    case_id = item._autotest_meta.get("case_id")
    if case_id and ("autotest_case_id", case_id) not in item.user_properties:
        # JUnit 是 Runner 回传 Hub 的稳定交换格式；函数名不包含业务用例编号，
        # 因此把编号写入 properties，避免云端执行报告变成 0 条结果。
        item.user_properties.append(("autotest_case_id", case_id))
    runtime = getattr(item.config, "autotest_runtime", None)
    if runtime:
        item.autotest_case_state = runtime.before_case(item.nodeid)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    report._autotest_meta = _case_meta(item)
    # 相机失败报告只显示整理后的异常信息，不展开 Python 源码和内部调用栈。
    if report.when == "call" and report.failed and item.nodeid.replace("\\", "/").find("testcases/camera/") >= 0:
        report.longrepr = str(call.excinfo.value) if call.excinfo else "相机用例执行失败"
    if report.when != "call":
        return

    runtime = getattr(item.config, "autotest_runtime", None)
    if not runtime:
        return

    status = "passed" if report.passed else "failed" if report.failed else "skipped"
    error_message = None
    if report.failed:
        error_message = str(report.longrepr)
    camera_evidence = next(
        (value for name, value in reversed(item.user_properties) if name == "camera_evidence"),
        None,
    )

    record = runtime.after_case(
        getattr(item, "autotest_case_state", {}),
        status,
        error_message=error_message,
        camera_evidence=camera_evidence,
    )

    if status == "passed" and record["status"] == "failed":
        report.outcome = "failed"
        report.longrepr = record["error_message"]

    if record["status"] in ("failed", "error"):
        execution_config = runtime.plan.get("execution", {})
        if execution_config.get("keep_on_fail", False):
            runtime.keep_failure_site()
            pytest.exit("Failure site kept; stopping execution as requested.", returncode=1)
        if not execution_config.get("continue_on_fail", True):
            pytest.exit("Test failed; stopping execution because continue_on_fail=false.", returncode=1)
