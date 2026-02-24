"""
输入验证模块。

提供用户输入的验证和 sanitization 功能。
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict, Any
from src.utils.logger import get_logger

logger = get_logger()


class InputValidationError(Exception):
    """输入验证错误异常。"""
    pass


class InputValidator:
    """
    输入验证器类。
    
    提供用户输入的验证和 sanitization 功能。
    """
    
    TOOL_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
    MAX_TOOL_NAME_LENGTH = 50
    MAX_PATH_LENGTH = 1024
    MAX_VERSION_LENGTH = 100
    
    @classmethod
    def validate_tool_name(cls, tool_name: str) -> bool:
        """
        验证工具名称的有效性。
        
        参数:
            tool_name: 工具名称
            
        返回:
            验证通过返回 True，否则抛出 InputValidationError
        """
        if not tool_name or not tool_name.strip():
            raise InputValidationError("工具名称不能为空")
        
        tool_name = tool_name.strip()
        
        if len(tool_name) > cls.MAX_TOOL_NAME_LENGTH:
            raise InputValidationError(f"工具名称不能超过 {cls.MAX_TOOL_NAME_LENGTH} 个字符")
        
        if not cls.TOOL_NAME_PATTERN.match(tool_name):
            raise InputValidationError("工具名称只能包含字母、数字、下划线和连字符")
        
        return True
    
    @classmethod
    def sanitize_tool_name(cls, tool_name: str) -> str:
        """
        sanitize 工具名称。
        
        参数:
            tool_name: 原始工具名称
            
        返回:
            sanitized 后的工具名称
        """
        if not tool_name:
            return ""
        tool_name = tool_name.strip().lower()
        return tool_name
    
    @classmethod
    def validate_path(cls, path: str) -> bool:
        """
        验证路径的有效性。
        
        参数:
            path: 路径字符串
            
        返回:
            验证通过返回 True，否则抛出 InputValidationError
        """
        if path is None:
            return True
        
        if len(path) > cls.MAX_PATH_LENGTH:
            raise InputValidationError(f"路径不能超过 {cls.MAX_PATH_LENGTH} 个字符")
        
        if '..' in path:
            raise InputValidationError("路径不能包含 ..")
        
        return True
    
    @classmethod
    def safe_join_path(cls, base_path: str, *paths: str) -> str:
        """
        安全连接路径，防止路径遍历。
        
        参数:
            base_path: 基础路径
            *paths: 要连接的路径部分
            
        返回:
            安全连接后的路径
            
        抛出:
            InputValidationError: 如果结果路径不在 base_path 外部
        """
        base = os.path.abspath(base_path)
        joined = os.path.abspath(os.path.join(base, *paths))
        if not joined.startswith(base + os.sep):
            raise InputValidationError(f"路径遍历检测: {joined}")
        return joined
    
    @classmethod
    def validate_json_config(cls, config_data: Dict[str, Any]) -> bool:
        """
        验证 JSON 配置的有效性。
        
        参数:
            config_data: 配置数据字典
            
        返回:
            验证通过返回 True，否则抛出 InputValidationError
        """
        if not isinstance(config_data, dict):
            raise InputValidationError("配置必须是字典类型")
        
        if "settings" in config_data:
            settings = config_data["settings"]
            if not isinstance(settings, dict):
                raise InputValidationError("settings 必须是字典类型")
            
            if "tool_templates" in settings:
                tool_templates = settings["tool_templates"]
                if not isinstance(tool_templates, dict):
                    raise InputValidationError("tool_templates 必须是字典类型")
                
                for tool_name, template in tool_templates.items():
                    try:
                        cls.validate_tool_name(tool_name)
                    except InputValidationError as e:
                        raise InputValidationError(f"工具 '{tool_name}': {e}") from e
        
        if "tools" in config_data:
            tools = config_data["tools"]
            if not isinstance(tools, dict):
                raise InputValidationError("tools 必须是字典类型")
        
        return True
    
    @classmethod
    def validate_version_string(cls, version: str) -> bool:
        """
        验证版本号字符串的有效性。
        
        参数:
            version: 版本号字符串
            
        返回:
            验证通过返回 True，否则抛出 InputValidationError
        """
        if not version or not version.strip():
            raise InputValidationError("版本号不能为空")
        
        if len(version.strip()) > cls.MAX_VERSION_LENGTH:
            raise InputValidationError(f"版本号不能超过 {cls.MAX_VERSION_LENGTH} 个字符")
        
        version_pattern = re.compile(r'^[a-zA-Z0-9._-]+$')
        if not version_pattern.match(version.strip()):
            raise InputValidationError("版本号格式无效")
        
        return True
    
    @classmethod
    def sanitize_version_string(cls, version: str) -> str:
        """
        sanitize 版本号字符串。
        
        参数:
            version: 原始版本号
            
        返回:
            sanitized 后的版本号
        """
        if not version:
            return ""
        return version.strip()
    
    @classmethod
    def validate_url(cls, url: str) -> bool:
        """
        验证 URL 的有效性。
        
        参数:
            url: URL 字符串
            
        返回:
            验证通过返回 True，否则抛出 InputValidationError
        """
        if not url or not url.strip():
            return True
        
        url_pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'
            r'(?:[A-Z]{2,63}|[A-Z0-9-]{2,})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$',
            re.IGNORECASE
        )
        
        if not url_pattern.match(url.strip()):
            raise InputValidationError("URL 格式无效")
        
        return True
    
    @classmethod
    def sanitize_url(cls, url: str) -> str:
        """
        sanitize URL 字符串。
        
        参数:
            url: 原始 URL
            
        返回:
            sanitized 后的 URL
        """
        if not url:
            return ""
        return url.strip()
    
    @classmethod
    def safe_get_config_value(cls, config: Dict[str, Any], key: str, default: Any = None) -> Any:
        """
        安全地获取配置值，避免 KeyError。
        
        参数:
            config: 配置字典
            key: 键名
            default: 默认值
            
        返回:
            配置值或默认值
        """
        try:
            keys = key.split('.')
            value = config
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k, default)
                else:
                    return default
            return value
        except Exception:
            return default
    
    @classmethod
    def validate_command_arg(cls, arg: str, max_length: int = 1024) -> bool:
        """
        验证命令参数的安全性，防止命令注入。
        
        参数:
            arg: 命令参数
            max_length: 最大长度
            
        返回:
            验证通过返回 True，否则抛出 InputValidationError
        """
        if arg is None:
            return True
        
        if len(arg) > max_length:
            raise InputValidationError(f"命令参数超过最大长度")
        
        dangerous_chars = [';', '|', '&', '>', '<', '`', '$', '\\', '"', "'"]
        for char in dangerous_chars:
            if char in arg:
                raise InputValidationError(f"命令参数包含非法字符: {char}")
        
        return True
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """
        sanitize 文件名，移除危险字符。
        
        参数:
            filename: 原始文件名
            
        返回:
            sanitized 后的文件名
        """
        if not filename:
            return ""
        
        invalid_chars = '<>:"/\\|?*'
        sanitized = ''.join(c for c in filename if c not in invalid_chars)
        
        sanitized = sanitized.strip()
        
        if sanitized in ['', '.', '..']:
            return "invalid_filename"
        
        return sanitized
