import argparse
import sys
import logging
from .core.runner import run_tests_locally
from .core.plan_parser import parse_test_plan
from .core.scaffold import init_project

def main():
    parser = argparse.ArgumentParser(description="AutoTestRunner - 智能硬件自动化测试本地引擎")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # init command
    init_parser = subparsers.add_parser("init", help="初始化标准自动化测试工程目录")
    init_parser.add_argument("project_name", default="my_autotest_project", nargs="?", help="项目名称")

    # run command
    run_parser = subparsers.add_parser("run", help="在本地执行测试用例")
    run_parser.add_argument("path", default="testcases/", nargs="?", help="测试用例路径")
    run_parser.add_argument("--plan", help="指定 YAML 测试计划文件")
    run_parser.add_argument("--hub-url", help="[协同模式] AutoTestHub 云端地址")
    run_parser.add_argument("--token", help="[协同模式] 云端鉴权 Token")

    # sync command
    sync_parser = subparsers.add_parser("sync", help="将本地用例元数据同步至云端")
    sync_parser.add_argument("path", default="testcases/", nargs="?", help="测试用例路径")
    sync_parser.add_argument("--hub-url", required=True, help="AutoTestHub 云端地址")
    sync_parser.add_argument("--token", required=True, help="云端鉴权 Token")

    args = parser.parse_args()

    if args.command == "init":
        success = init_project(args.project_name)
        sys.exit(0 if success else 1)

    elif args.command == "run":
        target_path = args.path
        if args.plan:
            targets = parse_test_plan(args.plan)
            if not targets:
                sys.exit(1)
            target_path = targets
            
        report_to_cloud = bool(args.hub_url and args.token)
        exit_code = run_tests_locally(target_path, report_to_cloud, args.hub_url, args.token)
        sys.exit(exit_code)
        
    elif args.command == "sync":
        logging.info(f"🔄 正在解析 {args.path} 目录下的多级文件夹结构与 @autotest 元数据...")
        logging.info("✅ 同步完成！本地文件夹结构将映射为云端的用例模块树。")
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
