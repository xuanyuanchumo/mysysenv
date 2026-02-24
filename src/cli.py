"""
Mysysenv 命令行接口模块。
"""

import argparse
import json
import sys
from typing import Optional

from src.core.config_manager import ConfigManager
from src.core.env_manager import EnvManager
from src.core.version_manager import VersionManager
from src.utils.logger import get_logger, setup_logger
from src.utils.permission_manager import is_admin

logger = get_logger()


def create_parser() -> argparse.ArgumentParser:
    """
    创建并配置命令行参数解析器。
    
    返回:
        配置好的 ArgumentParser 实例
    """
    parser = argparse.ArgumentParser(
        prog="mse",
        description="Mysysenv - 系统环境管理器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  mse                     启动图形界面模式
  mse list python         列出已安装的 Python 版本
  mse use python 3.10.4   切换到 Python 3.10.4
  mse install python 3.11 安装 Python 3.11
  mse root python D:\\py   设置 Python 根目录
  mse config              显示当前配置
        """,
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="启用详细输出",
    )
    
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        help="配置文件路径",
    )
    
    subparsers = parser.add_subparsers(
        dest="command",
        title="命令",
        description="可用的 CLI 命令",
    )
    
    list_parser = subparsers.add_parser(
        "list",
        help="列出工具的已安装版本",
    )
    list_parser.add_argument(
        "tool",
        nargs="?",
        default=None,
        help="工具名称 (python, java, node, maven, gradle)",
    )
    list_parser.add_argument(
        "--remote",
        "-r",
        action="store_true",
        help="显示远程可用版本",
    )
    list_parser.add_argument(
        "--format",
        "-f",
        choices=["table", "json", "simple"],
        default="simple",
        help="输出格式",
    )
    
    use_parser = subparsers.add_parser(
        "use",
        help="切换到指定版本",
    )
    use_parser.add_argument(
        "tool",
        help="工具名称 (python, java, node, maven, gradle)",
    )
    use_parser.add_argument(
        "version",
        help="要切换到的版本",
    )
    
    install_parser = subparsers.add_parser(
        "install",
        help="下载并安装指定版本",
    )
    install_parser.add_argument(
        "tool",
        help="工具名称 (python, java, node, maven, gradle)",
    )
    install_parser.add_argument(
        "version",
        help="要安装的版本",
    )
    
    uninstall_parser = subparsers.add_parser(
        "uninstall",
        help="卸载指定版本",
    )
    uninstall_parser.add_argument(
        "tool",
        help="工具名称 (python, java, node, maven, gradle)",
    )
    uninstall_parser.add_argument(
        "version",
        help="要卸载的版本",
    )
    
    root_parser = subparsers.add_parser(
        "root",
        help="设置或显示工具根目录",
    )
    root_parser.add_argument(
        "tool",
        help="工具名称 (python, java, node, maven, gradle)",
    )
    root_parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="根目录路径（省略则显示当前路径）",
    )
    
    config_parser = subparsers.add_parser(
        "config",
        help="显示或编辑配置",
    )
    config_parser.add_argument(
        "--edit",
        "-e",
        action="store_true",
        help="在编辑器中打开配置",
    )
    config_parser.add_argument(
        "--set",
        "-s",
        type=str,
        help="设置配置值（格式：key=value）",
    )
    
    tools_parser = subparsers.add_parser(
        "tools",
        help="列出所有已配置的工具",
    )
    
    return parser


def run_cli(args: argparse.Namespace) -> int:
    """
    运行命令行接口。
    
    参数:
        args: 解析后的命令行参数
        
    返回:
        退出码（0 表示成功）
    """
    if args.verbose:
        setup_logger(level=10)
    
    if not is_admin():
        print("警告：当前未以管理员权限运行。")
        print("某些操作可能会失败。建议以管理员身份运行。")
    
    if args.command is None:
        print("未指定命令。使用 --help 查看帮助信息。")
        return 1
    
    command_handlers = {
        "list": handle_list,
        "use": handle_use,
        "install": handle_install,
        "uninstall": handle_uninstall,
        "root": handle_root,
        "config": handle_config,
        "tools": handle_tools,
    }
    
    handler = command_handlers.get(args.command)
    if handler:
        return handler(args)
    else:
        print(f"未知命令: {args.command}")
        return 1


def _get_managers():
    """
    获取管理器实例。
    
    返回:
        包含 ConfigManager、EnvManager、VersionManager 的元组
    """
    config_manager = ConfigManager()
    env_manager = EnvManager()
    version_manager = VersionManager(config_manager, env_manager)
    return config_manager, env_manager, version_manager


def handle_list(args: argparse.Namespace) -> int:
    """
    处理 list 命令：列出已安装或远程可用的版本。
    
    参数:
        args: 解析后的命令行参数
        
    返回:
        退出码
    """
    config_manager, _, version_manager = _get_managers()
    
    if args.tool:
        tool = args.tool.lower()
        tool_templates = config_manager.get_tool_templates()
        
        if tool not in tool_templates:
            print(f"未知工具: {tool}")
            print(f"可用工具: {', '.join(tool_templates.keys())}")
            return 1
        
        if args.remote:
            print(f"正在获取 {tool} 的远程版本...")
            versions = version_manager.get_remote_versions(tool)
            if not versions:
                print(f"未找到 {tool} 的远程版本")
                return 0
            
            if args.format == "json":
                print(json.dumps(versions, indent=2))
            else:
                print(f"{tool} 可用版本:")
                for v in versions[:30]:
                    print(f"  {v['version']}")
                if len(versions) > 30:
                    print(f"  ... 还有 {len(versions) - 30} 个版本")
        else:
            versions = version_manager.scan_local_versions(tool)
            current = version_manager.get_current_version(tool)
            
            if not versions:
                print(f"未找到 {tool} 的已安装版本")
                root = config_manager.get_tool_root(tool)
                print(f"根目录: {root}")
                return 0
            
            if args.format == "json":
                result = {
                    "tool": tool,
                    "current": current,
                    "versions": versions
                }
                print(json.dumps(result, indent=2))
            else:
                print(f"{tool} 已安装版本:")
                for v in versions:
                    marker = " *" if v["version"] == current else "  "
                    print(f"{marker} {v['version']}")
                    if args.verbose:
                        print(f"     路径: {v['path']}")
                print(f"\n当前版本: {current or '未设置'}")
    else:
        tool_templates = config_manager.get_tool_templates()
        
        if args.format == "json":
            print(json.dumps(list(tool_templates.keys()), indent=2))
        else:
            print("已配置工具:")
            for tool_name, template in tool_templates.items():
                current = config_manager.get_config().get("tools", {}).get(tool_name, {}).get("current_version", "")
                print(f"  {tool_name}: {current or '未设置'}")
                if args.verbose:
                    print(f"    根目录: {template.get('tool_root', '')}")
    
    return 0


def handle_use(args: argparse.Namespace) -> int:
    """
    处理 use 命令：切换到指定版本。
    
    参数:
        args: 解析后的命令行参数
        
    返回:
        退出码
    """
    tool = args.tool.lower()
    version = args.version
    
    config_manager, _, version_manager = _get_managers()
    
    print(f"正在切换 {tool} 到版本 {version}...")
    
    if version_manager.switch_version(tool, version):
        print(f"成功切换 {tool} 到 {version}")
        print("注意：可能需要重启终端才能使更改生效。")
        return 0
    else:
        print(f"切换 {tool} 到 {version} 失败")
        return 1


def handle_install(args: argparse.Namespace) -> int:
    """
    处理 install 命令：下载并安装指定版本。
    
    参数:
        args: 解析后的命令行参数
        
    返回:
        退出码
    """
    tool = args.tool.lower()
    version = args.version
    
    config_manager, _, version_manager = _get_managers()
    
    print(f"正在安装 {tool} {version}...")
    
    def progress(downloaded: int, total: int):
        percent = int(downloaded / total * 100) if total > 0 else 0
        bar_len = 40
        filled = int(bar_len * percent / 100)
        bar = "=" * filled + "-" * (bar_len - filled)
        print(f"\r[{bar}] {percent}% ({downloaded}/{total} 字节)", end="", flush=True)
    
    if version_manager.download_version(tool, version, progress):
        print(f"\n成功安装 {tool} {version}")
        return 0
    else:
        print(f"\n安装 {tool} {version} 失败")
        return 1


def handle_uninstall(args: argparse.Namespace) -> int:
    """
    处理 uninstall 命令：卸载指定版本。
    
    参数:
        args: 解析后的命令行参数
        
    返回:
        退出码
    """
    tool = args.tool.lower()
    version = args.version
    
    config_manager, _, version_manager = _get_managers()
    
    current = version_manager.get_current_version(tool)
    if current == version:
        print(f"无法卸载当前正在使用的版本 {version}")
        return 1
    
    print(f"正在卸载 {tool} {version}...")
    
    if version_manager.delete_version(tool, version):
        print(f"成功卸载 {tool} {version}")
        return 0
    else:
        print(f"卸载 {tool} {version} 失败")
        return 1


def handle_root(args: argparse.Namespace) -> int:
    """
    处理 root 命令：设置或显示工具根目录。
    
    参数:
        args: 解析后的命令行参数
        
    返回:
        退出码
    """
    tool = args.tool.lower()
    
    config_manager = ConfigManager()
    tool_templates = config_manager.get_tool_templates()
    
    if args.path:
        new_path = args.path
        config = config_manager.get_config()
        if "settings" not in config:
            config["settings"] = {}
        settings = config["settings"]
        if "tool_templates" not in settings:
            settings["tool_templates"] = {}
        tool_templates = settings["tool_templates"]
        if tool not in tool_templates:
            tool_templates[tool] = {}
        tool_templates[tool]["tool_root"] = new_path
        config_manager.save_config(config)
        print(f"已设置 {tool} 根目录为: {new_path}")
    else:
        current_path = config_manager.get_tool_root(tool) or "未设置"
        print(f"{tool} 根目录: {current_path}")
    
    return 0


def handle_config(args: argparse.Namespace) -> int:
    """
    处理 config 命令：显示或编辑配置。
    
    参数:
        args: 解析后的命令行参数
        
    返回:
        退出码
    """
    config_manager = ConfigManager()
    config = config_manager.get_config()
    
    if args.set:
        key, _, value = args.set.partition("=")
        if not key or not value:
            print("格式无效。请使用: key=value")
            return 1
        
        keys = key.split(".")
        obj = config
        for k in keys[:-1]:
            if k not in obj:
                obj[k] = {}
            obj = obj[k]
        
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass
        
        obj[keys[-1]] = value
        config_manager.save_config(config)
        print(f"已设置 {key} = {value}")
    else:
        print(json.dumps(config, indent=2, ensure_ascii=False))
    
    return 0


def handle_tools(args: argparse.Namespace) -> int:
    """
    处理 tools 命令：列出所有已配置的工具。
    
    参数:
        args: 解析后的命令行参数
        
    返回:
        退出码
    """
    config_manager = ConfigManager()
    tool_templates = config_manager.get_tool_templates()
    
    print("已配置工具:")
    for tool_name, template in tool_templates.items():
        env_rule = template.get("env_rule", {})
        home_var = env_rule.get("home_var", "N/A")
        current = config_manager.get_config().get("tools", {}).get(tool_name, {}).get("current_version", "未设置")
        
        print(f"\n  {tool_name}:")
        print(f"    根目录: {template.get('tool_root', '未设置')}")
        print(f"    环境变量: {home_var}")
        print(f"    当前版本: {current}")
    
    return 0
