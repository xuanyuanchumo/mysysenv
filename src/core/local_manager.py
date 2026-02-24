"""
本地版本管理模块。

提供本地工具版本的扫描、验证和管理功能。
"""

import os
import re
import platform
import subprocess
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from src.utils.logger import get_logger
from src.core.config_manager import ConfigManager
from src.core.env_manager import EnvManager
from src.core.interfaces import ILocalManager
from src.utils.input_validator import InputValidator, InputValidationError

logger = get_logger()


class LocalManagerError(Exception):
    """本地管理错误异常。"""
    pass


class ToolNotFoundError(LocalManagerError):
    """工具未找到错误异常。"""
    pass


class VersionScanError(LocalManagerError):
    """版本扫描错误异常。"""
    pass


class LocalManager(ILocalManager):
    """
    本地版本管理器类。
    
    负责管理本地已安装的工具版本。
    实现 ILocalManager 抽象接口。
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化本地版本管理器。
        
        参数:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
    
    def get_tool_version_by_cmd(self, tool: str, tool_path: str) -> Optional[str]:
        """
        通过执行版本命令获取工具版本。
        
        参数:
            tool: 工具名称
            tool_path: 工具安装路径
            
        返回:
            版本字符串，获取失败返回 None
        """
        try:
            if not tool or not tool_path:
                logger.warning("获取工具版本失败: 参数不完整")
                return None
                
            version_cmd = self.config_manager.get_version_cmd(tool)
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
            
            logger.debug(f"执行命令获取 {tool} 版本: {executable}")
            
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
                    logger.debug(f"成功获取 {tool} 版本: {version}")
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
    
    def scan_local_versions(self, tool: str) -> List[Dict[str, Any]]:
        """
        扫描本地已安装的工具版本。
        
        参数:
            tool: 工具名称
            
        返回:
            版本信息列表，每个元素包含 version、path、install_date
        """
        try:
            try:
                InputValidator.validate_tool_name(tool)
            except InputValidationError as e:
                logger.error(f"工具名称验证失败: {e}")
                return []
                
            if not tool:
                logger.warning("扫描本地版本失败: 工具名称为空")
                return []
                
            root_path = self.config_manager.get_normalized_tool_root(tool)
            if not root_path or not os.path.exists(root_path):
                logger.info(f"工具 {tool} 的根目录不存在: {root_path}")
                return []
                
            logger.debug(f"开始扫描 {tool} 的本地版本，根目录: {root_path}")
            versions = []
            config = self.config_manager.get_config()
            existing_installed = config.get("tools", {}).get(tool, {}).get("installed_versions", [])
            current_version = config.get("tools", {}).get(tool, {}).get("current_version")
            existing_by_path = {v.get("path"): v for v in existing_installed}
            
            for item in os.listdir(root_path):
                try:
                    item_path = os.path.join(root_path, item)
                    if not os.path.isdir(item_path):
                        continue
                        
                    if self._validate_tool_installation(tool, item_path):
                        folder_version = self._extract_and_validate_version(tool, item)
                        real_version = self.get_tool_version_by_cmd(tool, item_path)
                        
                        if real_version:
                            version_str = real_version
                            if folder_version and folder_version != real_version:
                                logger.info(f"目录 {item} 文件夹版本 {folder_version} 与真实版本 {real_version} 不一致，将使用真实版本")
                        elif folder_version:
                            version_str = folder_version
                        else:
                            version_str = self._extract_version(tool, item)
                                
                        if not version_str:
                            logger.warning(f"无法确定目录 {item} 的版本，跳过")
                            continue
                            
                        install_date = datetime.fromtimestamp(
                            os.path.getctime(item_path)
                        ).isoformat()
                        
                        locked = False
                        is_system = False
                        if item_path in existing_by_path:
                            locked = existing_by_path[item_path].get("locked", False)
                            is_system = existing_by_path[item_path].get("is_system", False)
                        
                        if version_str == current_version and not is_system:
                            is_system = True
                        
                        versions.append({
                            "version": version_str,
                            "path": item_path,
                            "install_date": install_date,
                            "locked": locked,
                            "is_system": is_system
                        })
                except Exception as e:
                    logger.warning(f"处理目录 {item} 时出错: {e}")
                    continue
                    
            logger.info(f"找到 {len(versions)} 个 {tool} 本地版本")
            self._update_installed_versions_from_scan(tool, versions)
            return versions
            
        except OSError as e:
            logger.error(f"扫描 {tool} 本地版本时发生文件系统错误: {e}")
            return []
        except Exception as e:
            logger.error(f"扫描 {tool} 本地版本失败: {e}")
            return []
    
    def _update_installed_versions_from_scan(self, tool: str, versions: List[Dict[str, Any]]) -> None:
        """
        根据扫描结果更新配置中的已安装版本信息。
        
        参数:
            tool: 工具名称
            versions: 扫描到的版本列表
        """
        config = self.config_manager.get_config()
        if "tools" not in config:
            config["tools"] = {}
        if tool not in config["tools"]:
            config["tools"][tool] = {
                "installed_versions": [],
                "current_version": None
            }
        
        existing = config["tools"][tool].get("installed_versions", [])
        existing_paths = {v.get("path"): v for v in existing}
        
        updated_versions = []
        for v in versions:
            path = v["path"]
            if path in existing_paths:
                existing_v = existing_paths[path]
                existing_v["version"] = v["version"]
                existing_v["install_date"] = v["install_date"]
                updated_versions.append(existing_v)
            else:
                v["locked"] = v.get("locked", False)
                v["is_system"] = v.get("is_system", False)
                updated_versions.append(v)
        
        config["tools"][tool]["installed_versions"] = updated_versions
        
        current_version = config["tools"][tool].get("current_version")
        if current_version:
            for v in updated_versions:
                if v.get("path") and current_version.startswith(v.get("path", "")):
                    new_version = v.get("version")
                    if new_version and new_version != current_version:
                        logger.info(f"当前版本 {current_version} 路径对应的新版本为 {new_version}，更新 current_version")
                        config["tools"][tool]["current_version"] = new_version
                        break
        
        self.config_manager.save_config(config)
    
    def _validate_tool_installation(self, tool: str, path: str) -> bool:
        """
        验证工具安装是否有效。
        
        参数:
            tool: 工具名称
            path: 安装路径
            
        返回:
            有效返回 True，否则返回 False
        """
        validators = {
            "python": lambda p: os.path.exists(os.path.join(p, "python.exe")),
            "java": lambda p: os.path.exists(os.path.join(p, "bin", "java.exe")),
            "node": lambda p: os.path.exists(os.path.join(p, "node.exe")),
            "maven": lambda p: os.path.exists(os.path.join(p, "bin", "mvn.cmd")),
            "gradle": lambda p: os.path.exists(os.path.join(p, "bin", "gradle.bat")),
        }
        validator = validators.get(tool)
        if validator:
            return validator(path)
        return os.path.exists(path)
    
    def _extract_and_validate_version(self, tool: str, folder_name: str) -> Optional[str]:
        """
        从文件夹名称中提取并验证有效版本号。
        
        参数:
            tool: 工具名称
            folder_name: 文件夹名称
            
        返回:
            有效的版本字符串，提取失败或无效返回 None
        """
        patterns = {
            "python": r"python(\d+(?:\.\d+)*)",
            "java": r"jdk[-_]?(\d+\.?\d*\.?\d*)",
            "node": r"node[-_]?v?(\d+\.?\d*\.?\d*)",
            "maven": r"apache-maven[-_]?(\d+\.?\d*\.?\d*)",
            "gradle": r"gradle[-_]?(\d+\.?\d*\.?\d*)",
        }
        pattern = patterns.get(tool, r"(\d+\.?\d*\.?\d*)")
        match = re.search(pattern, folder_name, re.IGNORECASE)
        if match:
            version_str = match.group(1)
            if tool == "python":
                if "." in version_str:
                    validated = version_str
                elif len(version_str) >= 2:
                    major = version_str[0]
                    minor = version_str[1:]
                    validated = f"{major}.{minor}"
                else:
                    validated = version_str
            else:
                validated = version_str
            
            if self._is_valid_version(validated):
                return validated
        return None
    
    def _is_valid_version(self, version_str: str) -> bool:
        """
        验证版本字符串是否有效。
        
        参数:
            version_str: 版本字符串
            
        返回:
            有效返回 True，否则返回 False
        """
        if not version_str:
            return False
        parts = re.findall(r'\d+', version_str)
        return len(parts) >= 1 and all(part.isdigit() for part in parts)
    
    def _extract_version(self, tool: str, folder_name: str) -> str:
        """
        从文件夹名称中提取版本号（保持向后兼容性）。

        参数:
            tool: 工具名称
            folder_name: 文件夹名称

        返回:
            提取的版本字符串
        """
        patterns = {
            "python": r"python(\d+(?:\.\d+)*)",
            "java": r"jdk[-_]?(\d+\.?\d*\.?\d*)",
            "node": r"node[-_]?v?(\d+\.?\d*\.?\d*)",
            "maven": r"apache-maven[-_]?(\d+\.?\d*\.?\d*)",
            "gradle": r"gradle[-_]?(\d+\.?\d*\.?\d*)",
        }
        pattern = patterns.get(tool, r"(\d+\.?\d*\.?\d*)")
        match = re.search(pattern, folder_name, re.IGNORECASE)
        if match:
            version_str = match.group(1)
            if tool == "python":
                if "." in version_str:
                    return version_str
                if len(version_str) >= 2:
                    major = version_str[0]
                    minor = version_str[1:]
                    return f"{major}.{minor}"
                return version_str
            return version_str
        return folder_name

    def check_and_update_system_version(self, tool: str) -> Optional[Dict[str, str]]:
        """
        检查并更新工具的系统版本标记。

        比对系统环境变量中的工具路径与已安装版本列表，更新 is_system_version 字段。

        参数:
            tool: 工具名称

        返回:
            系统版本信息字典 {"version": str, "path": str}，如果系统版本不存在则返回 None
        """
        env_manager = EnvManager()
        system_version, system_path = env_manager.get_system_version(tool, self.config_manager)

        if not system_path:
            logger.debug(f"工具 {tool} 未找到系统环境变量")
            return None

        config = self.config_manager.get_config()
        tools_config = config.get("tools", {})
        tool_config = tools_config.get(tool, {})
        installed_versions = tool_config.get("installed_versions", [])

        if not installed_versions:
            logger.debug(f"工具 {tool} 没有已安装版本")
            return None

        has_changes = False
        for version_info in installed_versions:
            version_path = version_info.get("path", "")
            is_system = False

            if version_path and system_path:
                normalized_version_path = os.path.normpath(version_path).lower()
                normalized_system_path = os.path.normpath(system_path).lower()
                if normalized_version_path == normalized_system_path:
                    is_system = True

            if version_info.get("is_system") != is_system:
                version_info["is_system"] = is_system
                has_changes = True
                logger.debug(f"版本 {version_info.get('version')} 的 is_system 标记已更新为 {is_system}")

        if has_changes:
            self.config_manager.save_config(config)
            logger.info(f"工具 {tool} 的系统版本标记已更新")

        return {"version": system_version, "path": system_path}

    def get_system_version_from_env(self, tool: str) -> Optional[str]:
        """
        从系统环境变量获取当前工具版本。

        参数:
            tool: 工具名称

        返回:
            系统环境变量中的版本号，未找到返回 None
        """
        env_manager = EnvManager()
        system_version, system_path = env_manager.get_system_version(tool, self.config_manager)
        logger.info(f"[get_system_version_from_env] tool={tool}, system_version={system_version}, system_path={system_path}")
        return system_version
