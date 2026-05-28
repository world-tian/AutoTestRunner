import os
import logging
from pathlib import Path

def init_project(project_name="my_autotest_project"):
    """初始化标准测试项目目录结构"""
    base = Path(project_name)
    if base.exists():
        logging.error(f"❌ 目录 {project_name} 已存在，请换一个名称。")
        return False
        
    dirs = [
        "testcases",             # 存放用例代码，支持无限级子文件夹
        "testcases/network",     # 示例模块：网络
        "testcases/power",       # 示例模块：电源
        "plans",                 # 存放 YAML 测试计划
        "reports",               # 存放本地 HTML 报告和产物
        "logs",                  # 存放串口和设备运行日志
        "config",                # 存放全局配置文件
    ]
    
    for d in dirs:
        (base / d).mkdir(parents=True, exist_ok=True)
        # 添加 __init__.py 使其成为 Python 包
        if d.startswith("testcases"):
            (base / d / "__init__.py").touch()
            
    # 生成示例用例
    case_content = '''from autotest_runner import autotest

@autotest(case_id="TC-DEMO-01", title="示例：检查设备联网状态", priority="P1")
def test_device_online():
    """这是一个位于 network 模块下的示例用例"""
    assert True
'''
    (base / "testcases" / "network" / "test_online.py").write_text(case_content, encoding="utf-8")
    
    # 生成示例计划
    plan_content = '''name: "冒烟测试计划"
targets:
  - "testcases/"
env:
  DEVICE_IP: "192.168.1.100"
'''
    (base / "plans" / "smoke_plan.yaml").write_text(plan_content, encoding="utf-8")
    
    # 生成 conftest.py
    conftest_content = '''import pytest
# 此处可放置 pytest 全局夹具 (Fixtures) 和 Hook
'''
    (base / "testcases" / "conftest.py").write_text(conftest_content, encoding="utf-8")
    
    logging.info(f"✅ 成功初始化标准自动化测试工程: {project_name}")
    logging.info("📁 目录结构如下：")
    logging.info(f"  ├── testcases/  (用例管理，请在这里按模块建文件夹)")
    logging.info(f"  ├── plans/      (测试计划管理)")
    logging.info(f"  ├── reports/    (本地报告自动归档至此)")
    logging.info(f"  └── logs/       (执行日志归档)")
    return True
