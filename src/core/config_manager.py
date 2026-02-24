"""
配置管理器模块。

提供应用程序配置的加载、保存和验证功能。
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from src.utils.logger import get_logger
from src.core.interfaces import IConfigManager
from src.utils.input_validator import InputValidator, InputValidationError

logger = get_logger()


class ConfigValidationError(Exception):
    """配置验证错误异常。"""
    pass


class ConfigLoadError(Exception):
    """配置加载错误异常。"""
    pass


class ConfigSaveError(Exception):
    """配置保存错误异常。"""
    pass


def get_app_dir() -> Path:
    """
    获取应用程序目录路径。
    
    返回:
        应用程序所在目录的 Path 对象
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent


def _atomic_save_json(file_path: Path, data: Any, indent: int = 2) -> None:
    """
    原子保存 JSON 数据到文件，防止写入中断导致文件损坏。
    
    参数:
        file_path: 目标文件路径
        data: 要保存的数据
        indent: JSON 缩进
    """
    import os
    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        
        if os.name == 'nt':
            if file_path.exists():
                os.replace(temp_path, file_path)
            else:
                os.rename(temp_path, file_path)
        else:
            os.replace(temp_path, file_path)
            
    except Exception as e:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except:
                pass
        raise


class ConfigManager(IConfigManager):
    """
    配置管理器类。
    
    负责管理应用程序配置的加载、保存、验证和访问。
    实现 IConfigManager 抽象接口。
    """
    
    APP_DIR = get_app_dir()
    CONFIG_DIR = APP_DIR / "config"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    CACHE_FILE = CONFIG_DIR / "cache.json"
    DEFAULT_CONFIG_PATH = CONFIG_DIR / "default_config.json"

    REQUIRED_FIELDS = {
        "settings": dict,
        "tools": dict,
    }

    SETTINGS_FIELDS = {
        "tool_templates": dict,
        "cache_expire_time": int,
        "request_rate_limit": int,
        "download_retry_count": int,
        "download_speed_limit": int,
    }

    def __init__(self):
        """初始化配置管理器。"""
        self._config: dict[str, Any] = {}
        self._cache: dict[str, Any] = {}
        self._ensure_config_dir()
        self._ensure_default_config()

    def _ensure_config_dir(self) -> None:
        """确保配置目录存在。"""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    def _ensure_default_config(self) -> None:
        """确保默认配置文件存在，如果不存在则生成。"""
        if not self.DEFAULT_CONFIG_PATH.exists():
            default_config = self._get_builtin_default_config()
            self._save_default_config(default_config)

    def _get_builtin_default_config(self) -> dict[str, Any]:
        """获取内置默认配置。"""
        return {
            "settings": {
                "tool_templates": {
                    "python": {
                        "tool_root": "",
                        "mirror_list": [
                            "https://www.python.org/ftp/python/",
                            "https://mirrors.huaweicloud.com/python/",
                            "https://mirrors.aliyun.com/python/"
                        ],
                        "version_cmd": "python --version",
                        "env_rule": {
                            "home_var": "PYTHON_HOME",
                            "path_entries": ["", "Scripts"]
                        },
                        "version_fetch_config": {
                            "version_pattern": "href=\"(\\d+\\.\\d+\\.\\d+)/\"",
                            "download_url_template": "{mirror}{version}/python-{version}-embed-{arch}.zip",
                            "arch_map": {"x64": "amd64", "x86": "win32"}
                        }
                    },
                    "java": {
                        "tool_root": "",
                        "mirror_list": [
                            "https://mirrors.huaweicloud.com/openjdk/"
                        ],
                        "version_cmd": "java -version",
                        "env_rule": {
                            "home_var": "JAVA_HOME",
                            "path_entries": ["bin"]
                        },
                        "version_fetch_config": {
                            "version_pattern": "href=\"(\\d+(?:\\.\\d+)*)/\"",
                            "download_url_template": "{mirror}{version}/openjdk-{version}_windows-x64_bin.zip"
                        }
                    }
                },
                "cache_expire_time": 86400,
                "request_rate_limit": 10,
                "download_retry_count": 3,
                "download_speed_limit": 0,
            },
            "tools": {},
            "cache": str(self.CACHE_FILE.absolute()),
        }

    def _save_default_config(self, config: dict[str, Any]) -> None:
        """保存默认配置到文件。"""
        try:
            _atomic_save_json(self.DEFAULT_CONFIG_PATH, config, indent=2)
            logger.debug(f"默认配置已保存到 {self.DEFAULT_CONFIG_PATH}")
        except (IOError, OSError, json.JSONDecodeError) as e:
            logger.error(f"保存默认配置失败: {e}")
            raise ConfigSaveError(f"无法保存默认配置到 {self.DEFAULT_CONFIG_PATH}: {e}") from e

    def normalize_path(self, path: str) -> str:
        """
        规范化路径格式。
        
        参数:
            path: 原始路径字符串
            
        返回:
            规范化后的路径字符串
        """
        if not path:
            return path
        return str(Path(path))

    def get_default_config(self) -> dict[str, Any]:
        """
        获取默认配置。
        
        如果存在默认配置文件则从文件加载，否则返回内置默认配置。
        
        返回:
            默认配置字典
        """
        try:
            if self.DEFAULT_CONFIG_PATH.exists():
                logger.debug(f"从文件加载默认配置: {self.DEFAULT_CONFIG_PATH}")
                with open(self.DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
                    config = json.load(f)
            else:
                logger.debug("使用内置默认配置")
                config = self._get_builtin_default_config()
            
            config["cache"] = str(self.CACHE_FILE.absolute())
            return config
        except (IOError, OSError, json.JSONDecodeError) as e:
            logger.warning(f"加载默认配置文件失败，使用内置默认配置: {e}")
            config = self._get_builtin_default_config()
            config["cache"] = str(self.CACHE_FILE.absolute())
            return config

    def load_config(self) -> dict[str, Any]:
        """
        加载配置文件。
        
        如果配置文件不存在，则创建默认配置文件。
        
        返回:
            配置字典
        """
        try:
            if not self.CONFIG_FILE.exists():
                logger.info(f"配置文件不存在，创建默认配置: {self.CONFIG_FILE}")
                self._config = self.get_default_config()
                self.save_config()
                self._load_cache()
                return self._config

            logger.debug(f"从文件加载配置: {self.CONFIG_FILE}")
            with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                self._config = json.load(f)

            self._ensure_backward_compatibility()
            self._ensure_cache_field_correct()
            self.validate_config(self._config)
            self._load_cache()
            logger.debug("配置加载成功")
            return self._config
        except (IOError, OSError, json.JSONDecodeError) as e:
            logger.error(f"加载配置文件失败，使用默认配置: {e}")
            self._config = self.get_default_config()
            self._load_cache()
            return self._config
        except ConfigValidationError as e:
            logger.error(f"配置验证失败，使用默认配置: {e}")
            self._config = self.get_default_config()
            self._load_cache()
            return self._config

    def _ensure_cache_field_correct(self) -> None:
        """确保配置中的 cache 字段正确（总是存储 cache.json 的路径）。"""
        cache_path = str(self.CACHE_FILE.absolute())
        
        if "cache" in self._config and isinstance(self._config["cache"], dict):
            old_cache_data = self._config["cache"]
            self._config["cache"] = cache_path
            self._cache = old_cache_data
            self.save_cache()
            self.save_config()
        elif "cache" not in self._config or self._config["cache"] != cache_path:
            self._config["cache"] = cache_path
            self.save_config()

    def _ensure_backward_compatibility(self) -> None:
        """
        确保配置向后兼容，为旧版本配置添加新字段。
        """
        default_config = self.get_default_config()
        default_settings = default_config["settings"]
        
        if "settings" not in self._config:
            self._config["settings"] = {}
        
        settings = self._config["settings"]
        
        for field in ["cache_expire_time", "request_rate_limit", 
                      "download_retry_count", "download_speed_limit"]:
            if field not in settings:
                if field == "cache_expire_time":
                    settings[field] = 86400
                elif field == "request_rate_limit":
                    settings[field] = 10
                elif field == "download_retry_count":
                    settings[field] = 3
                elif field == "download_speed_limit":
                    settings[field] = 0
        
        if "tool_templates" not in settings:
            settings["tool_templates"] = default_settings.get("tool_templates", {})

    def _load_cache(self) -> None:
        """加载缓存文件。"""
        if self.CACHE_FILE.exists():
            try:
                with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception:
                self._cache = {}
        else:
            self._cache = {}

    def save_config(self, config: dict[str, Any] | None = None) -> None:
        """
        保存配置到文件。
        
        参数:
            config: 要保存的配置字典，如果为 None 则保存当前配置
        """
        try:
            if config is not None:
                self._config = config

            self.validate_config(self._config)

            config_to_save = self._config.copy()
            
            logger.debug(f"保存配置到 {self.CONFIG_FILE}")
            _atomic_save_json(self.CONFIG_FILE, config_to_save, indent=2)
            logger.debug("配置保存成功")
        except ConfigValidationError as e:
            logger.error(f"配置验证失败，无法保存: {e}")
            raise
        except (IOError, OSError, json.JSONDecodeError) as e:
            logger.error(f"保存配置失败: {e}")
            raise ConfigSaveError(f"无法保存配置到 {self.CONFIG_FILE}: {e}") from e

    def save_cache(self, cache: dict[str, Any] | None = None) -> None:
        """
        保存缓存到文件。
        
        参数:
            cache: 要保存的缓存字典，如果为 None 则保存当前缓存
        """
        try:
            if cache is not None:
                self._cache = cache

            logger.debug(f"保存缓存到 {self.CACHE_FILE}")
            _atomic_save_json(self.CACHE_FILE, self._cache, indent=2)
            logger.debug("缓存保存成功")
        except (IOError, OSError, json.JSONDecodeError) as e:
            logger.error(f"保存缓存失败: {e}")
            raise ConfigSaveError(f"无法保存缓存到 {self.CACHE_FILE}: {e}") from e

    def clear_cache(self) -> None:
        """
        清空缓存。
        """
        logger.info("清空缓存")
        self._cache = {}
        self.save_cache()
        logger.info("缓存已清空")

    def validate_config(self, config: dict[str, Any]) -> bool:
        """
        验证配置的有效性。
        
        参数:
            config: 要验证的配置字典
            
        返回:
            验证通过返回 True
            
        抛出:
            ConfigValidationError: 配置验证失败时抛出
        """
        try:
            for field, expected_type in self.REQUIRED_FIELDS.items():
                if field not in config:
                    raise ConfigValidationError(f"缺少必需字段: {field}")
                if not isinstance(config[field], expected_type):
                    raise ConfigValidationError(
                        f"字段 '{field}' 必须是 {expected_type.__name__} 类型，"
                        f"实际为 {type(config[field]).__name__}"
                    )

            settings = config["settings"]
            for field, expected_type in self.SETTINGS_FIELDS.items():
                if field not in settings:
                    raise ConfigValidationError(f"settings 中缺少必需字段: {field}")
                if not isinstance(settings[field], expected_type):
                    raise ConfigValidationError(
                        f"字段 'settings.{field}' 必须是 {expected_type.__name__} 类型，"
                        f"实际为 {type(settings[field]).__name__}"
                    )

            logger.debug("配置验证通过")
            return True
        except ConfigValidationError:
            raise
        except Exception as e:
            logger.error(f"配置验证过程发生未知错误: {e}")
            raise ConfigValidationError(f"配置验证失败: {e}") from e



    @property
    def config(self) -> dict[str, Any]:
        """
        获取配置字典（延迟加载）。
        
        返回:
            配置字典
        """
        if not self._config:
            self.load_config()
        return self._config

    def get_config(self) -> dict[str, Any]:
        """
        获取配置字典。
        
        返回:
            配置字典
        """
        return self.config

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取指定键的配置值。
        
        参数:
            key: 配置键名
            default: 默认值
            
        返回:
            配置值或默认值
        """
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        设置指定键的配置值。
        
        参数:
            key: 配置键名
            value: 配置值
        """
        self._config[key] = value

    def get_settings(self) -> dict[str, Any]:
        """
        获取 settings 配置部分。
        
        返回:
            settings 配置字典
        """
        return self.config.get("settings", {})

    def get_tool_templates(self) -> dict[str, Any]:
        """
        获取所有工具配置模板。
        
        返回:
            工具名称到配置模板的映射字典
        """
        return self.get_settings().get("tool_templates", {})
    
    def get_tool_template(self, tool: str) -> dict[str, Any]:
        """
        获取指定工具的配置模板。
        
        参数:
            tool: 工具名称
            
        返回:
            工具配置模板字典，如果未找到则返回空字典
        """
        templates = self.get_tool_templates()
        return templates.get(tool, {})
    
    def get_tool_root(self, tool: str) -> str:
        """
        获取指定工具的根目录路径。
        
        参数:
            tool: 工具名称
            
        返回:
            根目录路径，如果未配置则返回空字符串
        """
        template = self.get_tool_template(tool)
        return template.get("tool_root", "")
    
    def get_normalized_tool_root(self, tool: str) -> str:
        """
        获取指定工具的规范化根目录路径。
        
        参数:
            tool: 工具名称
            
        返回:
            规范化后的根目录路径
        """
        return self.normalize_path(self.get_tool_root(tool))
    
    def get_version_cmd(self, tool: str) -> str:
        """
        获取指定工具的版本检测命令。
        
        参数:
            tool: 工具名称
            
        返回:
            版本命令字符串，如果未配置则返回默认命令
        """
        template = self.get_tool_template(tool)
        return template.get("version_cmd", f"{tool} --version")
    
    def get_env_rule(self, tool: str) -> dict[str, Any]:
        """
        获取指定工具的环境变量规则。
        
        参数:
            tool: 工具名称
            
        返回:
            环境变量规则字典，如果未配置则返回默认规则
        """
        template = self.get_tool_template(tool)
        env_rule = template.get("env_rule", {})
        if not env_rule:
            return {
                "home_var": f"{tool.upper()}_HOME",
                "path_entries": [""]
            }
        return env_rule
    
    def get_mirror_list(self, tool: str) -> list[str]:
        """
        获取指定工具的镜像源列表。
        
        参数:
            tool: 工具名称
            
        返回:
            镜像 URL 列表
        """
        template = self.get_tool_template(tool)
        return template.get("mirror_list", [])
    
    def get_version_fetch_config(self, tool: str) -> dict[str, Any]:
        """
        获取指定工具的版本获取配置。
        
        参数:
            tool: 工具名称
            
        返回:
            版本获取配置字典
        """
        template = self.get_tool_template(tool)
        return template.get("version_fetch_config", {})

    def get_cache_expire_time(self) -> int:
        """
        获取缓存过期时间配置（秒）。
        
        返回:
            缓存过期时间（秒）
        """
        return self.get_settings().get("cache_expire_time", 86400)

    def get_request_rate_limit(self) -> int:
        """
        获取请求频率限制配置（次/秒）。
        
        返回:
            请求频率限制
        """
        return self.get_settings().get("request_rate_limit", 10)

    def get_download_retry_count(self) -> int:
        """
        获取下载重试次数配置。
        
        返回:
            下载重试次数
        """
        return self.get_settings().get("download_retry_count", 3)

    def get_download_speed_limit(self) -> int:
        """
        获取下载速度限制配置（字节/秒，0 表示不限制）。
        
        返回:
            下载速度限制
        """
        return self.get_settings().get("download_speed_limit", 0)

    def get_tools(self) -> dict[str, Any]:
        """
        获取工具配置部分。
        
        返回:
            tools 配置字典
        """
        return self.config.get("tools", {})

    def get_cache(self) -> dict[str, Any]:
        """
        获取缓存配置部分。
        
        返回:
            cache 配置字典
        """
        return self._cache

    def set_cache(self, key: str, value: Any) -> None:
        """
        设置缓存值。
        
        参数:
            key: 缓存键名
            value: 缓存值
        """
        self._cache[key] = value

    def reset_to_default(self) -> dict[str, Any]:
        """
        重置配置为默认配置（用 default_config.json 的内容完全覆盖）。
        
        返回:
            更新后的配置字典
        """
        default_config = self.get_default_config()
        self._config = default_config
        self.save_config()
        return self._config

    def add_tool_config(self, tool_name: str) -> bool:
        """
        添加新工具配置。
        
        参数:
            tool_name: 工具名称
            
        返回:
            成功返回 True，工具已存在返回 False
        """
        from ..utils.logger import get_logger
        
        logger = get_logger()
        
        try:
            InputValidator.validate_tool_name(tool_name)
        except InputValidationError as e:
            logger.error(f"工具名称验证失败: {e}")
            return False
            
        tool_name = InputValidator.sanitize_tool_name(tool_name)
        if not tool_name:
            return False
            
        if "settings" not in self._config:
            self._config["settings"] = {}
        settings = self._config["settings"]
        
        tool_templates = settings.get("tool_templates", {})
        if tool_name in tool_templates:
            return False
        
        default_settings = self._get_builtin_default_config()["settings"]
        for key in ["tool_templates", "cache_expire_time", "request_rate_limit", 
                    "download_retry_count", "download_speed_limit"]:
            if key not in settings:
                settings[key] = default_settings[key] if key in default_settings else {}
        
        template_settings = self.get_default_config().get("settings", {})
        default_templates = template_settings.get("tool_templates", {})
        default_template = default_templates.get(tool_name)
        
        if default_template:
            logger.info(f"检测到工具 '{tool_name}' 的预定义配置，正在自动填充...")
            tool_templates[tool_name] = default_template
            logger.info(f"工具 '{tool_name}' 的预定义配置填充完成")
        else:
            tool_templates[tool_name] = {
                "tool_root": "",
                "mirror_list": [""],
                "version_cmd": f"{tool_name} --version",
                "env_rule": {
                    "home_var": f"{tool_name.upper()}_HOME",
                    "path_entries": [""]
                },
                "version_fetch_config": {
                    "version_pattern": "href=\"(\\d+\\.\\d+\\.\\d+)/\"",
                    "download_url_template": f"{{mirror}}{{version}}/{tool_name}-{{version}}.zip"
                }
            }
            logger.info(f"工具 '{tool_name}' 无预定义配置，已创建空白配置")
        
        settings["tool_templates"] = tool_templates
        
        if "tools" not in self._config:
            self._config["tools"] = {}
        if tool_name not in self._config["tools"]:
            self._config["tools"][tool_name] = {
                "installed_versions": [],
                "current_version": None
            }
        
        self.save_config()
        return True
    
    def get_tool_specific_config(self, tool_name: str) -> dict[str, Any]:
        """
        获取工具特定配置。
        
        参数:
            tool_name: 工具名称
            
        返回:
            工具特定配置字典
        """
        tool_template = self.get_tool_template(tool_name)
        tool_config = {}
        
        if "tool_root" in tool_template:
            tool_config["tool_root"] = tool_template["tool_root"]
        
        if "version_cmd" in tool_template:
            tool_config["version_cmd"] = tool_template["version_cmd"]
        
        if "mirror_list" in tool_template:
            tool_config["mirror_list"] = tool_template["mirror_list"]
        
        if "version_fetch_config" in tool_template:
            tool_config["version_fetch_config"] = tool_template["version_fetch_config"]
        
        if "env_rule" in tool_template:
            tool_config["env_rule"] = tool_template["env_rule"]
        
        return tool_config
    
    def save_tool_specific_config(self, tool_name: str, tool_config: dict[str, Any]) -> bool:
        """
        保存工具特定配置。
        
        参数:
            tool_name: 工具名称
            tool_config: 工具配置字典
            
        返回:
            保存成功返回 True，失败返回 False
        """
        try:
            try:
                InputValidator.validate_tool_name(tool_name)
            except InputValidationError as e:
                logger.error(f"工具名称验证失败: {e}")
                return False
            
            if "mirror_list" in tool_config:
                mirror_list = tool_config["mirror_list"]
                if isinstance(mirror_list, list):
                    for url in mirror_list:
                        if url:
                            try:
                                InputValidator.validate_url(url)
                            except InputValidationError as e:
                                logger.error(f"镜像 URL 验证失败: {e}")
                                return False
            
            if "tool_root" in tool_config:
                tool_root = tool_config["tool_root"]
                if tool_root:
                    try:
                        InputValidator.validate_path(tool_root)
                    except InputValidationError as e:
                        logger.error(f"路径验证失败: {e}")
                        return False
            
            current_config = self.get_config()
            settings = current_config.get("settings", {})
            tool_templates = settings.get("tool_templates", {})
            
            if tool_name not in tool_templates:
                tool_templates[tool_name] = {}
            
            tool_template = tool_templates[tool_name]
            
            if "tool_root" in tool_config:
                tool_template["tool_root"] = tool_config["tool_root"]
            
            if "version_cmd" in tool_config:
                tool_template["version_cmd"] = tool_config["version_cmd"]
            
            if "mirror_list" in tool_config:
                tool_template["mirror_list"] = tool_config["mirror_list"]
            
            if "version_fetch_config" in tool_config:
                tool_template["version_fetch_config"] = tool_config["version_fetch_config"]
            
            if "env_rule" in tool_config:
                tool_template["env_rule"] = tool_config["env_rule"]
            
            settings["tool_templates"] = tool_templates
            current_config["settings"] = settings
            self.save_config(current_config)
            return True
        except Exception as e:
            from ..utils.logger import get_logger
            logger = get_logger()
            logger.error(f"保存工具特定配置失败: {e}")
            return False
    
    def set_tool_root_config(self, tool: str, path: str) -> bool:
        """
        设置工具根目录配置。
        
        参数:
            tool: 工具名称
            path: 根目录路径
            
        返回:
            成功返回 True
        """
        try:
            InputValidator.validate_tool_name(tool)
            if path:
                InputValidator.validate_path(path)
        except InputValidationError as e:
            logger.error(f"参数验证失败: {e}")
            return False
            
        config = self.get_config()
        if "settings" not in config:
            config["settings"] = {}
        settings = config["settings"]
        if "tool_templates" not in settings:
            settings["tool_templates"] = {}
        tool_templates = settings["tool_templates"]
        if tool not in tool_templates:
            tool_templates[tool] = {}
        tool_templates[tool]["tool_root"] = path
        self.save_config(config)
        return True
    
    def delete_tool_config(self, tool_name: str) -> bool:
        """
        删除工具配置。
        
        参数:
            tool_name: 工具名称
            
        返回:
            成功返回 True，失败返回 False
        """
        try:
            try:
                InputValidator.validate_tool_name(tool_name)
            except InputValidationError as e:
                logger.error(f"工具名称验证失败: {e}")
                return False
                
            tool_name = InputValidator.sanitize_tool_name(tool_name)
            
            config = self.get_config()
            settings = config.get("settings", {})
            
            tool_templates = settings.get("tool_templates", {})
            if tool_name in tool_templates:
                del tool_templates[tool_name]
            
            if tool_name in config.get("tools", {}):
                del config["tools"][tool_name]
            
            config["settings"] = settings
            self.save_config(config)
            return True
        except Exception as e:
            from ..utils.logger import get_logger
            logger = get_logger()
            logger.error(f"删除工具配置失败: {e}")
            return False
