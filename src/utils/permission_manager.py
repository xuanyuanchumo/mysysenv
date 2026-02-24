import ctypes
import sys
import os


def is_admin() -> bool:
    """
    检测当前进程是否具有管理员权限。
    
    Returns:
        bool: 如果具有管理员权限返回 True，否则返回 False
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_as_admin(params: str = "") -> None:
    """
    请求以管理员权限重新运行当前程序。
    
    使用 ShellExecuteW 以 "runas" 操作重新启动程序，
    这会触发 UAC 提示框请求用户授权。
    
    Args:
        params: 传递给程序的命令行参数，默认为空字符串
    
    Raises:
        OSError: 如果调用 ShellExecuteW 失败
    """
    if sys.platform != "win32":
        raise OSError("权限提升仅支持 Windows 平台")
    
    executable = sys.executable
    script = os.path.abspath(sys.argv[0])
    
    if params:
        params = f'"{script}" {params}'
    else:
        params = f'"{script}"'
    
    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        executable,
        params,
        None,
        1
    )
    
    if result <= 32:
        raise OSError(f"ShellExecuteW 调用失败，返回值: {result}")
