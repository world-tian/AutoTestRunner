import yaml
import logging
import os

def parse_test_plan(plan_file):
    """解析 YAML 测试计划，返回 pytest 需要的参数和环境变量"""
    if not os.path.exists(plan_file):
        logging.error(f"❌ 测试计划文件不存在: {plan_file}")
        return None
        
    with open(plan_file, 'r', encoding='utf-8') as f:
        plan = yaml.safe_load(f)
        
    logging.info(f"📋 加载测试计划: {plan.get('name', 'Unnamed Plan')}")
    
    # 提取目标用例路径
    targets = plan.get('targets', [])
    
    # 提取环境变量
    env_vars = plan.get('env', {})
    for k, v in env_vars.items():
        os.environ[k] = str(v)
        
    return targets
