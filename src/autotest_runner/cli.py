import argparse
import sys
import logging
import os
from pathlib import Path
from .core.runner import run_tests_locally
from .core.plan_parser import load_test_plan
from .core.scaffold import init_project


def _resolve_plan(path):
    """从工作区根目录运行时，自动定位 autotestrunner/plans 下的计划。"""
    candidate = Path(path)
    if candidate.is_file():
        return str(candidate)
    package_root = Path(__file__).resolve().parents[2]
    nested = package_root / candidate
    if nested.is_file():
        logging.info("📍 自动定位测试计划: %s -> %s", path, nested)
        return str(nested)
    return path

def main():
    parser = argparse.ArgumentParser(description="AutoTestRunner - 智能硬件自动化测试本地引擎")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # init command
    init_parser = subparsers.add_parser("init", help="初始化标准自动化测试工程目录")
    init_parser.add_argument("project_name", default="my_autotest_project", nargs="?", help="项目名称")

    # run command
    run_parser = subparsers.add_parser("run", help="在本地执行测试用例")
    run_parser.add_argument("path", default="testcases/", nargs="?", help="测试用例路径")
    run_parser.add_argument("-plan", "--plan", help="指定 YAML 测试计划文件")
    run_parser.add_argument("--hub-url", help="[协同模式] AutoTestHub 云端地址")
    run_parser.add_argument("--token", help="[协同模式] 云端鉴权 Token")
    run_parser.add_argument("--project-id", help="AutoTestHub 项目 ID；提供后运行前自动同步用例")
    run_parser.add_argument("-pic", "--picture", help="相机单次运行图片文件或目录，覆盖 CAMERA_CONFIG")
    run_parser.add_argument("--sfr-stars", help="图卡矫正平面中的西门子星 ROI JSON，覆盖专项 plan 的 SFR_STAR_REGIONS")
    run_parser.add_argument("--allow-failures", action="store_true", help="保留失败报告但让命令返回0，适合输入不完整的探索性相机回归")

    # sync command
    sync_parser = subparsers.add_parser("sync", help="将本地用例元数据同步至云端")
    sync_parser.add_argument("path", default="testcases/", nargs="?", help="测试用例路径")
    sync_parser.add_argument("--hub-url", required=True, help="AutoTestHub 云端地址")
    sync_parser.add_argument("--token", help="云端鉴权 Token（本地无鉴权部署可省略）")
    sync_parser.add_argument("--project-id", required=True, help="目标项目 ID，防止同步到错误项目")

    args = parser.parse_args()

    if args.command == "init":
        success = init_project(args.project_name)
        sys.exit(0 if success else 1)

    elif args.command == "run":
        hub_url = args.hub_url or os.getenv("AUTOTEST_HUB_URL")
        token = args.token or os.getenv("AUTOTEST_HUB_TOKEN")
        project_id = args.project_id or os.getenv("AUTOTEST_PROJECT_ID")
        if project_id:
            os.environ["AUTOTEST_PROJECT_ID"] = project_id
        target_path = args.path
        plan_config = None
        if args.plan:
            plan_config = load_test_plan(_resolve_plan(args.plan))
            if not plan_config:
                sys.exit(1)
            # targets 可省略；默认递归收集所有模块的 testcases。
            target_path = plan_config.get("targets") or ["testcases"]
            if not (hub_url and project_id):
                logging.warning("⚠️ 当前仅执行本地测试：未提供 Hub 地址或项目 ID，不会同步用例或报告到 AutoTestHub")
        if args.picture:
            os.environ["CAMERA_PICTURE"] = args.picture
        if args.sfr_stars:
            os.environ["SFR_STAR_REGIONS"] = args.sfr_stars
        if plan_config and plan_config.get("input", {}).get("require_picture"):
            picture = os.getenv("CAMERA_PICTURE")
            if not picture:
                logging.error("❌ 此专项计划需要实拍测试图；请用 --picture 指定图片路径，不能使用仓库中的流程示意图。")
                sys.exit(2)
            if not Path(picture).is_file():
                logging.error("❌ 实拍测试图不存在: %s", picture)
                sys.exit(2)
        cloud_sync_ready = bool(hub_url and project_id)
        if cloud_sync_ready:
            from .core.sync import sync_cases
            sync_root_path = Path(__file__).resolve().parents[2] / "testcases"
            configured_root = Path(target_path[0]) if isinstance(target_path, list) and target_path else Path("testcases")
            if configured_root.is_absolute() and configured_root.exists():
                sync_root_path = configured_root
            elif (Path.cwd() / configured_root).exists():
                sync_root_path = (Path.cwd() / configured_root).resolve()
            elif (Path(__file__).resolve().parents[2] / configured_root).exists():
                sync_root_path = (Path(__file__).resolve().parents[2] / configured_root).resolve()
            # 计划 target 可能是 camera/output 等深层目录，同步必须从包含 catalog.json 的用例根目录开始。
            if not any(sync_root_path.rglob("catalog.json")):
                sync_root_path = Path(__file__).resolve().parents[2] / "testcases"
            sync_root = str(sync_root_path)
            try:
                logging.info("✅ AutoTestHub 用例同步完成: %s", sync_cases(sync_root, hub_url, token, project_id))
            except Exception as exc:
                cloud_sync_ready = False
                logging.warning(
                    "⚠️ AutoTestHub 不可用或用例同步失败，将继续本地测试；本次结果仅保存在本地，不上传云端: %s",
                    exc,
                )
            
        report_to_cloud = cloud_sync_ready
        exit_code = run_tests_locally(target_path, report_to_cloud, hub_url, token, plan_config=plan_config, allow_failures=args.allow_failures)
        sys.exit(exit_code)
        
    elif args.command == "sync":
        from .core.sync import sync_cases
        try:
            result = sync_cases(args.path, args.hub_url, args.token, args.project_id)
            logging.info("同步完成: %s", result)
        except Exception as exc:
            logging.error("同步失败: %s", exc)
            sys.exit(1)
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
