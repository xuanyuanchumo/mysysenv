"""
环境变量管理器模块。

提供 Windows 系统环境变量的读取、设置和管理功能。
"""

import os
import winreg
import ctypes
from typing import Optional, List, Tuple
from src.utils.logger import get_logger
from src.core.interfaces import IEnvManager

logger = get_logger()

ENV_KEY_PATH = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
ENV_KEY_ROOT = winreg.HKEY_LOCAL_MACHINE
WM_SETTINGCHANGE = 0x001A
HWND_BROADCAST = 0xFFFF
SMTO_ABORTIFHUNG = 0x0002


class EnvManagerError(Exception):
    """环境变量管理错误异常。"""
    pass


class RegistryAccessError(EnvManagerError):
    """注册表访问错误异常。"""
    pass


class EnvManager(IEnvManager):
    """
    环境变量管理器类。
    
    负责管理 Windows 系统环境变量，包括读取、设置、删除等操作。
    实现 IEnvManager 抽象接口。
    """
    
    def __init__(self):
        """初始化环境变量管理器。"""
        self._key = None

    def _open_key(self, writable: bool = True):
        """
        打开注册表环境变量键。
        
        参数:
            writable: 是否以可写模式打开
            
        返回:
            打开的注册表键句柄，失败返回 None
        """
        access = winreg.KEY_READ | winreg.KEY_SET_VALUE if writable else winreg.KEY_READ
        try:
            self._key = winreg.OpenKey(ENV_KEY_ROOT, ENV_KEY_PATH, 0, access)
            logger.debug(f"注册表键已打开 (writable={writable})")
            return self._key
        except WindowsError as e:
            error_msg = f"打开注册表键失败: {e}"
            logger.error(error_msg)
            raise RegistryAccessError(error_msg) from e

    def _close_key(self):
        """关闭注册表键。"""
        if self._key is not None:
            try:
                winreg.CloseKey(self._key)
            except (TypeError, OSError):
                pass
            self._key = None

    def get_env_var(self, name: str) -> Optional[str]:
        """
        获取环境变量值。
        
        参数:
            name: 环境变量名称
            
        返回:
            环境变量值，不存在则返回 None
        """
        try:
            key = self._open_key(writable=False)
            value, _ = winreg.QueryValueEx(key, name)
            self._close_key()
            logger.debug(f"读取环境变量 {name}={value}")
            return value
        except FileNotFoundError:
            logger.debug(f"环境变量 {name} 不存在")
            return None
        except RegistryAccessError:
            return None
        except WindowsError as e:
            error_msg = f"读取环境变量 {name} 失败: {e}"
            logger.error(error_msg)
            return None
        finally:
            self._close_key()

    def set_env_var(self, name: str, value: str) -> bool:
        """
        设置环境变量值。
        
        参数:
            name: 环境变量名称
            value: 环境变量值
            
        返回:
            设置成功返回 True，失败返回 False
        """
        try:
            key = self._open_key(writable=True)
            reg_type = winreg.REG_EXPAND_SZ if "%" in value else winreg.REG_SZ
            winreg.SetValueEx(key, name, 0, reg_type, value)
            self._close_key()
            logger.info(f"设置环境变量 {name}={value}")
            self.broadcast_change()
            return True
        except RegistryAccessError:
            return False
        except WindowsError as e:
            error_msg = f"设置环境变量 {name} 失败: {e}"
            logger.error(error_msg)
            return False
        finally:
            self._close_key()

    def delete_env_var(self, name: str) -> bool:
        """
        删除环境变量。
        
        参数:
            name: 环境变量名称
            
        返回:
            删除成功返回 True，失败返回 False
        """
        try:
            key = self._open_key(writable=True)
            winreg.DeleteValue(key, name)
            self._close_key()
            logger.info(f"删除环境变量 {name}")
            self.broadcast_change()
            return True
        except FileNotFoundError:
            logger.debug(f"环境变量 {name} 不存在，无需删除")
            return True
        except RegistryAccessError:
            return False
        except WindowsError as e:
            error_msg = f"删除环境变量 {name} 失败: {e}"
            logger.error(error_msg)
            return False
        finally:
            self._close_key()

    def get_path_entries(self) -> List[str]:
        """
        获取 PATH 环境变量的所有条目。
        
        返回:
            PATH 条目列表
        """
        try:
            path_value = self.get_env_var("PATH")
            if not path_value:
                return []
            entries = [e.strip() for e in path_value.split(";") if e.strip()]
            return entries
        except Exception as e:
            logger.error(f"获取 PATH 条目失败: {e}")
            return []

    def add_to_path(self, entry: str) -> bool:
        """
        向 PATH 环境变量添加新条目。
        
        参数:
            entry: 要添加的路径条目
            
        返回:
            添加成功返回 True，失败返回 False
        """
        try:
            if not entry or not entry.strip():
                logger.warning("PATH 条目不能为空")
                return False
                
            entries = self.get_path_entries()
            normalized_entry = entry.strip().rstrip("\\")
            for existing in entries:
                if existing.rstrip("\\").lower() == normalized_entry.lower():
                    logger.debug(f"PATH 已包含 {entry}")
                    return True
            entries.append(normalized_entry)
            new_path = ";".join(entries)
            result = self.set_env_var("PATH", new_path)
            if result:
                logger.info(f"已添加 {entry} 到 PATH")
            return result
        except Exception as e:
            logger.error(f"添加 PATH 条目失败: {e}")
            return False

    def remove_from_path(self, entry: str) -> bool:
        """
        从 PATH 环境变量移除条目。
        
        参数:
            entry: 要移除的路径条目
            
        返回:
            移除成功返回 True，失败返回 False
        """
        try:
            if not entry or not entry.strip():
                logger.warning("要移除的 PATH 条目不能为空")
                return True
                
            entries = self.get_path_entries()
            normalized_entry = entry.strip().rstrip("\\").lower()
            new_entries = [
                e for e in entries
                if e.rstrip("\\").lower() != normalized_entry
            ]
            if len(new_entries) == len(entries):
                logger.debug(f"PATH 不包含 {entry}")
                return True
            new_path = ";".join(new_entries)
            result = self.set_env_var("PATH", new_path)
            if result:
                logger.info(f"已从 PATH 移除 {entry}")
            return result
        except Exception as e:
            logger.error(f"移除 PATH 条目失败: {e}")
            return False

    def path_contains(self, entry: str) -> bool:
        """
        检查 PATH 是否包含指定条目。
        
        参数:
            entry: 要检查的路径条目
            
        返回:
            包含返回 True，否则返回 False
        """
        try:
            if not entry or not entry.strip():
                return False
                
            entries = self.get_path_entries()
            normalized_entry = entry.strip().rstrip("\\").lower()
            for existing in entries:
                if existing.rstrip("\\").lower() == normalized_entry:
                    return True
            return False
        except Exception as e:
            logger.error(f"检查 PATH 条目失败: {e}")
            return False

    def broadcast_change(self) -> None:
        """
        广播环境变量更改消息。
        
        通知系统和其他应用程序环境变量已更改。
        """
        try:
            result = ctypes.c_long()
            ctypes.windll.user32.SendMessageTimeoutW(
                HWND_BROADCAST,
                WM_SETTINGCHANGE,
                0,
                "Environment",
                SMTO_ABORTIFHUNG,
                5000,
                ctypes.byref(result)
            )
            logger.debug("已广播 WM_SETTINGCHANGE 消息")
        except Exception as e:
            logger.warning(f"广播环境变量更改消息失败: {e}")

    def setup_tool_env(self, tool: str, home_var: str, path: str, path_entries: List[str]) -> bool:
        """
        设置工具的环境变量。
        
        配置工具的 HOME 变量和 PATH 条目。
        
        参数:
            tool: 工具名称
            home_var: HOME 环境变量名称
            path: 工具安装路径
            path_entries: 要添加到 PATH 的子目录列表
            
        返回:
            设置成功返回 True，失败返回 False
        """
        try:
            if not tool or not home_var or not path:
                logger.error(f"设置工具环境变量失败: 参数不完整")
                return False
                
            if not self.set_env_var(home_var, path):
                logger.error(f"设置 {home_var} 环境变量失败")
                return False
                
            for entry in path_entries:
                full_entry = f"%{home_var}%\\{entry}" if entry else f"%{home_var}%"
                if not self.path_contains(full_entry):
                    if not self.add_to_path(full_entry):
                        logger.warning(f"添加 {full_entry} 到 PATH 失败")
            logger.info(f"已设置 {tool} 环境变量")
            return True
        except Exception as e:
            logger.error(f"设置 {tool} 环境变量失败: {e}")
            return False

    def get_all_env_vars(self) -> dict:
        """
        获取所有系统环境变量。
        
        返回:
            环境变量名称到值的映射字典
        """
        try:
            key = self._open_key(writable=False)
            result = {}
            index = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, index)
                    result[name] = value
                    index += 1
                except OSError:
                    break
            self._close_key()
            logger.debug(f"已获取 {len(result)} 个环境变量")
            return result
        except RegistryAccessError:
            return {}
        except WindowsError as e:
            error_msg = f"获取所有环境变量失败: {e}"
            logger.error(error_msg)
            return {}
        finally:
            self._close_key()

    def get_system_version(self, tool_name: str, config_manager: 'ConfigManager') -> Tuple[Optional[str], Optional[str]]:
        """
        获取系统环境中的工具版本。

        参数:
            tool_name: 工具名称
            config_manager: 配置管理器实例

        返回:
            元组 (version, path)，如果环境变量不存在或版本获取失败则返回 (None, None)
        """
        try:
            env_rule = config_manager.get_env_rule(tool_name)
            home_var = env_rule.get("home_var")
            if not home_var:
                logger.debug(f"工具 {tool_name} 未配置 home_var")
                return (None, None)

            path = os.environ.get(home_var)
            if not path:
                path = self.get_env_var(home_var)

            if not path:
                logger.debug(f"系统环境变量 {home_var} 不存在")
                return (None, None)

            logger.debug(f"获取到系统环境变量 {home_var}={path}")

            version = self._get_version_from_path(tool_name, path, config_manager)
            return (version, path)
        except Exception as e:
            logger.error(f"获取系统 {tool_name} 版本失败: {e}")
            return (None, None)

    def _get_version_from_path(self, tool: str, tool_path: str, config_manager: 'ConfigManager') -> Optional[str]:
        """
        通过执行版本命令获取工具版本。

        参数:
            tool: 工具名称
            tool_path: 工具安装路径
            config_manager: 配置管理器实例

        返回:
            版本字符串，获取失败返回 None
        """
        import subprocess
        import re

        try:
            version_cmd = config_manager.get_version_cmd(tool)
            if not version_cmd:
                logger.debug(f"未配置 {tool} 的版本命令")
                return None

            tool_executables = {
                "python": os.path.join(tool_path, "python.exe"),
                "java": os.path.join(tool_path, "bin", "java.exe"),
                "node": os.path.join(tool_path, "node.exe"),
                "maven": os.path.join(tool_path, "bin", "mvn.cmd"),
                "gradle": os.path.join(tool_path, "bin", "gradle.bat"),
            }

            executable = tool_executables.get(tool)
            if not executable or not os.path.exists(executable):
                logger.debug(f"可执行文件不存在: {executable}")
                return None

            if tool == "python":
                cmd = [executable, "--version"]
            elif tool == "java":
                cmd = [executable, "-version"]
            elif tool == "node":
                cmd = [executable, "-v"]
            elif tool == "maven":
                cmd = [executable, "-version"]
            elif tool == "gradle":
                cmd = [executable, "-version"]
            else:
                return None

            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            output = result.stdout + result.stderr

            version_patterns = {
                "python": r"Python (\d+\.\d+\.\d+)",
                "java": r'version "?(\d+\.?\d*\.?\d*)',
                "node": r"v?(\d+\.\d+\.\d+)",
                "maven": r"Apache Maven (\d+\.\d+\.\d+)",
                "gradle": r"Gradle (\d+\.\d+(?:\.\d+)?)",
            }

            pattern = version_patterns.get(tool)
            if pattern:
                match = re.search(pattern, output, re.IGNORECASE)
                if match:
                    version = match.group(1)
                    logger.debug(f"成功获取系统环境 {tool} 版本: {version}")
                    return version

            logger.debug(f"无法从输出中解析 {tool} 版本")
            return None
        except subprocess.TimeoutExpired:
            logger.warning(f"获取 {tool} 版本超时 (10秒)")
            return None
        except FileNotFoundError as e:
            logger.warning(f"文件未找到: {e}")
            return None
        except PermissionError as e:
            logger.error(f"权限不足，无法执行命令: {e}")
            return None
        except Exception as e:
            logger.error(f"获取 {tool} 版本失败: {e}")
            return None
