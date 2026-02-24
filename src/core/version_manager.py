"""
版本管理器模块。

提供工具版本的扫描、下载、安装、切换和删除功能。
"""

import os
import re
import shutil
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable

from src.utils.logger import get_logger
from src.core.config_manager import ConfigManager
from src.core.env_manager import EnvManager
from src.core.remote_fetcher import RemoteFetcher, MirrorStatus
from src.core.local_manager import LocalManager
from src.core.download_manager import DownloadManager
from src.core import version_utils
from src.core.interfaces import IVersionManager
from src.utils.input_validator import InputValidator, InputValidationError

logger = get_logger()


class VersionManagerError(Exception):
    """版本管理错误异常。"""
    pass


class VersionNotFoundError(VersionManagerError):
    """版本未找到错误异常。"""
    pass


class VersionLockedError(VersionManagerError):
    """版本已锁定错误异常。"""
    pass


class SwitchVersionError(VersionManagerError):
    """切换版本错误异常。"""
    pass


class DeleteVersionError(VersionManagerError):
    """删除版本错误异常。"""
    pass


class VersionManager(IVersionManager):
    """
    版本管理器类。
    
    负责管理开发工具的版本，包括本地版本扫描、远程版本获取、
    下载安装、版本切换和删除等功能。
    
    本类作为协调者，将具体工作委托给各个专用模块。
    实现 IVersionManager 抽象接口。
    """
    
    def __init__(self, config_manager: ConfigManager, env_manager: EnvManager):
        """
        初始化版本管理器。
        
        参数:
            config_manager: 配置管理器实例
            env_manager: 环境变量管理器实例
        """
        self.config_manager = config_manager
        self.env_manager = env_manager
        
        self.remote_fetcher = RemoteFetcher(config_manager)
        self.local_manager = LocalManager(config_manager)
        self.download_manager = DownloadManager(config_manager)
        
        self.mirror_status = self.remote_fetcher.mirror_status
        self._memory_cache: Dict[str, Any] = {}
    
    def get_tool_version_by_cmd(self, tool: str, tool_path: str) -> Optional[str]:
        """
        通过执行版本命令获取工具版本。
        
        参数:
            tool: 工具名称
            tool_path: 工具安装路径
            
        返回:
            版本字符串，获取失败返回 None
        """
        return self.local_manager.get_tool_version_by_cmd(tool, tool_path)
    
    def scan_local_versions(self, tool: str) -> List[Dict[str, Any]]:
        """
        扫描本地已安装的工具版本。
        
        参数:
            tool: 工具名称
            
        返回:
            版本信息列表，每个元素包含 version、path、install_date
        """
        return self.local_manager.scan_local_versions(tool)
    
    def get_remote_versions(self, tool: str, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        获取远程可用的工具版本。
        
        参数:
            tool: 工具名称
            use_cache: 是否使用缓存
            
        返回:
            远程版本信息列表
        """
        return self.remote_fetcher.get_remote_versions(tool, use_cache)
    
    def get_version_info(self, tool: str, version: str) -> Optional[Dict[str, Any]]:
        """
        从缓存或远程获取指定版本的详细信息。
        
        参数:
            tool: 工具名称
            version: 版本号
            
        返回:
            版本信息字典，未找到返回 None
        """
        cache_key = f"{tool}_versions"
        if cache_key in self._memory_cache:
            cached = self._memory_cache[cache_key]
            for v in cached.get("versions", []):
                if v.get("version") == version:
                    return v
        
        versions = self.get_remote_versions(tool, use_cache=True)
        for v in versions:
            if v.get("version") == version:
                return v
        return None
    
    def sort_versions_desc(self, versions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        按版本号降序排列版本列表。
        
        参数:
            versions: 版本信息列表
            
        返回:
            排序后的版本列表
        """
        return version_utils.sort_versions_desc(versions)
    
    def group_versions_by_major(self, versions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        按主版本号分组版本列表。
        
        参数:
            versions: 版本信息列表
            
        返回:
            分组后的版本列表，每个分组包含 major_version 和 versions
        """
        return version_utils.group_versions_by_major(versions)
    
    def download_version(
        self,
        tool: str,
        version: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        status_callback: Optional[Callable[[str], None]] = None,
        version_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        下载并安装指定版本，支持断点续传和重试。
        
        参数:
            tool: 工具名称
            version: 版本号
            progress_callback: 下载进度回调函数
            status_callback: 状态消息回调函数
            version_info: 版本信息字典（可选，包含 download_url）
            
        返回:
            成功返回 True，失败返回 False
        """
        mirror_list = self.remote_fetcher.get_mirror_list(tool)
        return self.download_manager.download_version(
            tool, version, progress_callback, status_callback, version_info,
            self.mirror_status, mirror_list
        )
    
    def switch_version(self, tool: str, version: str) -> bool:
        """
        切换到指定版本。
        
        参数:
            tool: 工具名称
            version: 版本号
            
        返回:
            成功返回 True，失败返回 False
        """
        try:
            try:
                InputValidator.validate_tool_name(tool)
                InputValidator.validate_version_string(version)
            except InputValidationError as e:
                logger.error(f"参数验证失败: {e}")
                return False
                
            if not tool or not version:
                logger.error("切换版本失败: 参数不完整")
                return False
                
            logger.info(f"正在切换 {tool} 到版本 {version}")
            config = self.config_manager.get_config()
            tools_config = config.get("tools", {}).get(tool, {})
            installed = tools_config.get("installed_versions", [])
            version_info = next((v for v in installed if v["version"] == version), None)
            
            if not version_info:
                local_versions = self.scan_local_versions(tool)
                version_info = next((v for v in local_versions if v["version"] == version), None)
                if not version_info:
                    error_msg = f"{tool} 版本 {version} 未安装"
                    logger.error(error_msg)
                    return False
                    
            path = version_info["path"]
            env_rule = self.config_manager.get_env_rule(tool)
            home_var = env_rule.get("home_var")
            path_entries = env_rule.get("path_entries", [])
            
            if not home_var:
                logger.error(f"未配置 {tool} 的 home_var")
                return False
                
            if not self.env_manager.setup_tool_env(tool, home_var, path, path_entries):
                logger.error(f"设置 {tool} {version} 环境变量失败")
                return False
                
            if "tools" not in config:
                config["tools"] = {}
            if tool not in config["tools"]:
                config["tools"][tool] = {"installed_versions": [], "current_version": None}
                
            current_version = tools_config.get("current_version")
            if current_version:
                current_info = next((v for v in installed if v["version"] == current_version), None)
                if current_info:
                    current_info["is_system"] = False
                    
            version_info["is_system"] = True
            config["tools"][tool]["current_version"] = version
            self.config_manager.save_config(config)
            logger.info(f"已切换 {tool} 到版本 {version}")
            return True
            
        except Exception as e:
            logger.error(f"切换 {tool} 到版本 {version} 时发生错误: {e}")
            return False
    
    def get_current_version(self, tool: str) -> Optional[str]:
        """
        获取当前使用的版本。
        
        参数:
            tool: 工具名称
            
        返回:
            当前版本号，未设置返回 None
        """
        config = self.config_manager.get_config()
        config_version = config.get("tools", {}).get(tool, {}).get("current_version")
        if config_version:
            return config_version
        env_version = self.local_manager.get_system_version_from_env(tool)
        if env_version:
            return env_version
        return None
    
    def lock_version(self, tool: str, version: str, locked: bool) -> bool:
        """
        锁定或解锁指定版本。
        
        参数:
            tool: 工具名称
            version: 版本号
            locked: 是否锁定
            
        返回:
            成功返回 True，失败返回 False
        """
        try:
            InputValidator.validate_tool_name(tool)
            InputValidator.validate_version_string(version)
        except InputValidationError as e:
            logger.error(f"参数验证失败: {e}")
            return False
            
        config = self.config_manager.get_config()
        tools_config = config.get("tools", {}).get(tool, {})
        installed = tools_config.get("installed_versions", [])
        version_info = next((v for v in installed if v["version"] == version), None)
        if not version_info:
            logger.error(f"未找到 {tool} 版本 {version}")
            return False
        version_info["locked"] = locked
        self.config_manager.save_config(config)
        action = "锁定" if locked else "解锁"
        logger.info(f"{action} {tool} 版本 {version}")
        return True
    
    def delete_version(self, tool: str, version: str) -> bool:
        """
        删除指定版本。
        
        参数:
            tool: 工具名称
            version: 版本号
            
        返回:
            成功返回 True，失败返回 False
        """
        try:
            InputValidator.validate_tool_name(tool)
            InputValidator.validate_version_string(version)
        except InputValidationError as e:
            logger.error(f"参数验证失败: {e}")
            return False
            
        config = self.config_manager.get_config()
        tools_config = config.get("tools", {}).get(tool, {})
        installed = tools_config.get("installed_versions", [])
        version_info = next((v for v in installed if v["version"] == version), None)
        if not version_info:
            logger.error(f"未找到 {tool} 版本 {version}")
            return False
        if version_info.get("locked", False):
            logger.error(f"{tool} 版本 {version} 已被锁定，无法删除")
            return False
        if version_info.get("is_system", False):
            logger.error(f"{tool} 版本 {version} 是系统标记版本，无法删除")
            return False
        path = version_info["path"]
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
                logger.info(f"已删除 {path}")
            installed.remove(version_info)
            if tools_config.get("current_version") == version:
                config["tools"][tool]["current_version"] = None
            self.config_manager.save_config(config)
            return True
        except Exception as e:
            logger.error(f"删除 {tool} {version} 失败: {e}")
            return False

    def check_and_update_system_version(self, tool: str):
        """
        检查并更新工具的系统版本标记。

        参数:
            tool: 工具名称
        """
        self.local_manager.check_and_update_system_version(tool)
    

