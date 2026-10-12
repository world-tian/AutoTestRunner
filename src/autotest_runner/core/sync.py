"""从显式用例目录同步可审阅的元数据，不导入或执行硬件脚本。"""
import ast
import json
from pathlib import Path

import requests


def collect_cases(root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError(f"用例目录不存在: {root}")
    cases = []
    for manifest in sorted(root.rglob("catalog.json")):
        for item in json.loads(manifest.read_text(encoding="utf-8")):
            # 目录内脚本必须真实存在，防止目录清单与可运行用例漂移。
            script = (manifest.parent / item['script_path']).resolve()
            if not script.is_relative_to(root) or not script.is_file():
                raise ValueError(f"无效脚本路径: {script}")
            tree = ast.parse(script.read_text(encoding="utf-8"))
            if not any(isinstance(n, ast.FunctionDef) and n.name == item['function'] for n in tree.body):
                raise ValueError(f"脚本缺少函数: {script}::{item['function']}")
            cases.append({**{k: item[k] for k in ('local_case_id', 'title', 'priority', 'feature', 'test_class', 'description', 'preconditions', 'steps', 'expected_result')},
                          'case_category': 'automated',
                          'script_path': f"{script.relative_to(root).as_posix()}::{item['function']}"})
    if not cases:
        raise ValueError("未找到 catalog.json 用例清单；未执行同步")
    ids = [c['local_case_id'] for c in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("用例清单存在重复编号")
    return cases


def sync_cases(root, hub_url, token, project_id):
    cases = collect_cases(root)
    response = requests.post(f"{hub_url.rstrip('/')}/api/sync/test-cases",
                             headers={"Authorization": f"Bearer {token}"} if token else {},
                             json={"project_id": project_id, "test_cases": cases}, timeout=(3, 30))
    response.raise_for_status()
    result = response.json()
    if result.get('created', 0) + result.get('updated', 0) != len(cases):
        raise ValueError(f"同步计数不一致: {result}")
    return result
