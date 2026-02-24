"""
Mysysenv 应用程序主入口点。
"""

import sys
import ctypes
from pathlib import Path
from typing import Optional


def setup_import_path() -> None:
    """
    设置正确的导入路径，确保模块能正常导入。
    """
    src_dir = Path(__file__).resolve().parent
    project_root = src_dir.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


setup_import_path()

from src.cli import create_parser, run_cli
from src.ui import run_gui
from src.utils.permission_manager import is_admin, run_as_admin


def show_admin_confirm_dialog() -> bool:
    """
    显示管理员权限确认对话框。

    Returns:
        bool: 用户点击"是"返回 True，点击"否"返回 False
    """
    MB_YESNO = 0x00000004
    MB_ICONQUESTION = 0x00000020
    IDYES = 6
    IDNO = 7

    result = ctypes.windll.user32.MessageBoxW(
        None,
        "此程序需要管理员权限才能正常运行某些功能。\n\n是否现在获取管理员权限？",
        "管理员权限请求",
        MB_YESNO | MB_ICONQUESTION
    )

    return result == IDYES


def main(args: Optional[list[str]] = None) -> int:
    """
    应用程序主入口点。
    
    参数:
        args: 命令行参数。如果为 None，将使用 sys.argv[1:]。
    
    返回:
        退出码（0 表示成功，非零表示错误）。
    """
    if not is_admin() and sys.platform == "win32":
        if show_admin_confirm_dialog():
            run_as_admin()
            sys.exit(0)

    parser = create_parser()
    parsed_args = parser.parse_args(args)
    
    if parsed_args.command:
        return run_cli(parsed_args)
    else:
        return run_gui(parsed_args)


if __name__ == "__main__":
    sys.exit(main())
