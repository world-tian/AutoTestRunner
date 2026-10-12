"""统计相机用例目录；可选地把统计结果写回 README 的标记区间。"""
import argparse
import json
from pathlib import Path


CAMERA_ROOT = Path(__file__).resolve().parent
TESTCASES_ROOT = CAMERA_ROOT.parent
README = CAMERA_ROOT / "README.md"
START = "<!-- CAMERA_CASE_COUNTS_START -->"
END = "<!-- CAMERA_CASE_COUNTS_END -->"


def collect():
    scripts = sorted(TESTCASES_ROOT.rglob("test_*.py"))
    rows = []
    for script in scripts:
        relative = script.relative_to(TESTCASES_ROOT).parts
        module = relative[1] if len(relative) > 1 and relative[0] == "camera" else (relative[0] if relative else "-")
        priority = next((part for part in relative if part in {"P0", "P1", "P2", "P3"}), "-")
        rows.append((module, priority, script))
    return rows


def render(rows):
    total = len(rows)
    camera_rows = [row for row in rows if row[2].is_relative_to(CAMERA_ROOT)]
    modules = {}
    priorities = {}
    cases = {}
    for module, priority, script in camera_rows:
        modules[module] = modules.get(module, 0) + 1
        priorities[(module, priority)] = priorities.get((module, priority), 0) + 1
        case_dir = script.parent.relative_to(TESTCASES_ROOT).as_posix()
        cases[case_dir] = cases.get(case_dir, 0) + 1
    lines = [START, f"- `testcases`（{total}条）", f"- `testcases/camera`（{len(camera_rows)}条）"]
    lines.extend(f"- `testcases/camera/{module}`（{count}条）" for module, count in sorted(modules.items()))
    lines.extend(
        f"- `testcases/camera/{module}/{priority}`（{count}条）"
        for (module, priority), count in sorted(priorities.items())
    )
    lines.extend(f"- `testcases/{case_dir}`（{count}条）" for case_dir, count in sorted(cases.items()))
    lines.append(END)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-readme", action="store_true")
    args = parser.parse_args()
    rows = collect()
    text = render(rows)
    print(text)
    if args.update_readme:
        content = README.read_text(encoding="utf-8")
        start = content.find(START)
        end = content.find(END)
        if start < 0 or end < 0 or end < start:
            raise ValueError("README 缺少用例统计标记区间")
        end += len(END)
        README.write_text(content[:start] + text + content[end:], encoding="utf-8")


if __name__ == "__main__":
    main()