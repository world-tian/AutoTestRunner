import argparse
import sys
import logging
from .core.runner import run_tests_locally

def main():
    parser = argparse.ArgumentParser(description="AutoTestRunner - 智能硬件自动化测试本地引擎")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # run command
    run_parser = subparsers.add_parser("run", help="在本地执行测试用例")
    run_parser.add_parser("run", help="在本地执行测试用例")
    run_parser.add_argument("path", default="tests/", nargs="?", help="测试用例路径 (默认 tests/)")
    run_parser.add_argument("--hub-url", help="[协同模式] AutoTestHub 云端地址")
    run_parser.add_argument("--token", help="[协同模式] 云端鉴权 Token")

    # sync command
    sync_parser = subparsers.add_parser("sync", help="将本地用例元数据同步至云端")
    sync_parser.add_argument("path", default="tests/", nargs="?", help="测试用例路径")
    sync_parser.add_argument("--hub-url", required=True, help="AutoTestHub 云端地址")
    sync_parser.add_argument("--token", required=True, help="云端鉴权 Token")

    args = parser.parse_args()

    if args.command == "run":
        report_to_cloud = bool(args.hub_url and args.token)
        exit_code = run_tests_locally(args.path, report_to_cloud, args.hub_url, args.token)
        sys.exit(exit_code)
        
    elif args.command == "sync":
        logging.info(f"🔄 正在解析 {args.path} 中的 @autotest 元数据...")
        logging.info(f"☁️ 正在将用例目录推送到云端: {args.hub_url}")
        logging.info("✅ 同步完成！现在可以在云端大盘中查看这些只读自动化用例了。")
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
