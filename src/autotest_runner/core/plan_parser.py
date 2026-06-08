import yaml
import logging
import os

DEFAULT_PLAN = {
    "name": "Unnamed Plan",
    "targets": [],
    "env": {},
    "execution": {
        "continue_on_fail": True,
        "keep_on_fail": False,
        "keep_on_fail_timeout_sec": 0,
        "cleanup_between_cases": True,
    },
    "serial": {
        "enabled": False,
        "port": "/dev/ttyUSB0",
        "baudrate": 115200,
        "log": True,
        "fail_patterns": [],
        "pass_patterns": [],
        "timeout_sec": 10,
    },
    "adb": {
        "enabled": False,
        "device_id": "",
        "clear_logcat_before_case": True,
        "collect_on_fail": {
            "logcat": True,
            "bugreport": False,
            "screenshot": True,
            "pull_paths": [],
        },
    },
    "cleanup": {
        "enabled": False,
        "actions": [],
    },
    "artifacts": {
        "output_dir": "reports/artifacts",
        "zip_logs": True,
    },
}


def _deep_merge(defaults, data):
    result = dict(defaults)
    for key, value in (data or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_test_plan(plan_file):
    """解析 YAML 测试计划，返回完整执行配置。"""
    if not os.path.exists(plan_file):
        logging.error(f"❌ 测试计划文件不存在: {plan_file}")
        return None
        
    with open(plan_file, 'r', encoding='utf-8') as f:
        raw_plan = yaml.safe_load(f) or {}

    plan = _deep_merge(DEFAULT_PLAN, raw_plan)
        
    logging.info(f"📋 加载测试计划: {plan.get('name', 'Unnamed Plan')}")

    env_vars = plan.get('env', {})
    for k, v in env_vars.items():
        os.environ[k] = str(v)
        
    return plan


def parse_test_plan(plan_file):
    """兼容旧接口：只返回 pytest 目标路径。"""
    plan = load_test_plan(plan_file)
    if not plan:
        return None
    return plan.get("targets", [])
