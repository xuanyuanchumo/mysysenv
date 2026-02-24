"""
配置数据提供模块。

负责配置数据的管理，包括配置的加载、保存等。
"""

import json
from typing import Dict, Any
from PySide6.QtCore import QObject, Signal, Property

from src.core.config_manager import ConfigManager
from src.utils.logger import get_logger
from src.utils.input_validator import InputValidator, InputValidationError

logger = get_logger()


class ConfigDataProvider(QObject):
    """
    配置数据提供类。
    
    负责配置数据的管理，包括配置的加载、保存等。
    """

    configJsonChanged = Signal()

    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        初始化配置数据提供器。
        
        参数:
            config_manager: 配置管理器实例
            parent: 父对象
        """
        logger.info("[CONFIG_DATA] __init__(): 开始初始化 ConfigDataProvider")
        super().__init__(parent)
        self._config_manager = config_manager
        self._config_json: str = ""
        logger.info("[CONFIG_DATA] __init__(): ConfigDataProvider 初始化完成")

    @Property(str, notify=configJsonChanged)
    def configJson(self) -> str:
        """获取配置 JSON 字符串。"""
        return self._config_json

    @configJson.setter
    def configJson(self, value: str):
        """设置配置 JSON 字符串。"""
        if self._config_json != value:
            old_value = self._config_json
            self._config_json = value
            logger.info(f"[CONFIG_DATA] configJson 变更: 旧值长度={len(old_value)}, 新值长度={len(value)}")
            self.configJsonChanged.emit()

    def load_config(self):
        """加载全局配置（只返回 settings 部分）。"""
        logger.info("[CONFIG_DATA] load_config(): 开始加载全局配置")
        config = self._config_manager.get_config()
        settings = config.get("settings", {})
        self._config_json = json.dumps(settings, indent=2, ensure_ascii=False)
        self.configJsonChanged.emit()
        logger.info(f"[CONFIG_DATA] load_config(): 配置加载完成，长度={len(self._config_json)}")

    def load_tool_specific_config(self, tool_name: str):
        """加载工具特定配置。"""
        logger.info(f"[CONFIG_DATA] load_tool_specific_config(): 开始加载工具配置，工具={repr(tool_name)}")
        tool_config = self._config_manager.get_tool_specific_config(tool_name)
        self._config_json = json.dumps(tool_config, indent=2, ensure_ascii=False)
        self.configJsonChanged.emit()
        logger.info(f"[CONFIG_DATA] load_tool_specific_config(): 工具配置加载完成，长度={len(self._config_json)}")

    def save_config(self, config_json: str) -> bool:
        """保存全局配置。"""
        logger.info(f"[CONFIG_DATA] save_config(): 开始保存全局配置，配置长度={len(config_json)}")
        try:
            new_settings = json.loads(config_json)
        except json.JSONDecodeError as e:
            logger.error(f"[CONFIG_DATA] save_config(): JSON 格式无效: {e}")
            return False

        try:
            temp_config = {"settings": new_settings}
            InputValidator.validate_json_config(temp_config)
        except InputValidationError as e:
            logger.error(f"[CONFIG_DATA] save_config(): 配置验证失败: {e}")
            return False

        try:
            current_config = self._config_manager.get_config()
            current_config["settings"] = new_settings
            self._config_manager.save_config(current_config)
            logger.info("[CONFIG_DATA] save_config(): 全局配置保存成功")
            self._config_json = json.dumps(new_settings, indent=2, ensure_ascii=False)
            self.configJsonChanged.emit()
            return True
        except Exception as e:
            logger.error(f"[CONFIG_DATA] save_config(): 异常: {e}", exc_info=True)
            return False

    def save_tool_specific_config(self, tool_name: str, config_json: str) -> bool:
        """保存工具特定配置。"""
        logger.info(f"[CONFIG_DATA] save_tool_specific_config(): 开始保存工具配置，工具={repr(tool_name)}, 配置长度={len(config_json)}")
        
        try:
            InputValidator.validate_tool_name(tool_name)
        except InputValidationError as e:
            logger.error(f"[CONFIG_DATA] save_tool_specific_config(): 工具名称验证失败: {e}")
            return False

        try:
            tool_config = json.loads(config_json)
        except json.JSONDecodeError as e:
            logger.error(f"[CONFIG_DATA] save_tool_specific_config(): JSON 格式无效: {e}")
            return False

        try:
            if self._config_manager.save_tool_specific_config(tool_name, tool_config):
                logger.info(f"[CONFIG_DATA] save_tool_specific_config(): 工具 {repr(tool_name)} 配置保存成功")
                self._config_json = json.dumps(tool_config, indent=2, ensure_ascii=False)
                self.configJsonChanged.emit()
                return True
            else:
                logger.error(f"[CONFIG_DATA] save_tool_specific_config(): 工具 {repr(tool_name)} 配置保存失败")
                return False
        except Exception as e:
            logger.error(f"[CONFIG_DATA] save_tool_specific_config(): 异常: {e}", exc_info=True)
            return False

    def reset_to_default(self) -> Dict[str, Any]:
        """重置配置为默认配置。"""
        logger.info("[CONFIG_DATA] reset_to_default(): 开始重置配置为默认值")
        default_config = self._config_manager.reset_to_default()
        default_settings = default_config.get("settings", {})
        self._config_json = json.dumps(default_settings, indent=2, ensure_ascii=False)
        self.configJsonChanged.emit()
        logger.info("[CONFIG_DATA] reset_to_default(): 配置已重置为默认值")
        return default_config

    def get_tool_config_json(self) -> str:
        """获取 settings 字段的配置 JSON 字符串。"""
        logger.debug("[CONFIG_DATA] get_tool_config_json(): 开始获取工具配置 JSON")
        config = self._config_manager.get_config()
        settings = config.get("settings", {})
        result = json.dumps(settings, indent=2, ensure_ascii=False)
        logger.debug(f"[CONFIG_DATA] get_tool_config_json(): 获取完成，配置长度={len(result)}")
        return result

    def set_tool_root(self, tool: str, path: str) -> bool:
        """设置工具根目录。"""
        logger.info(f"[CONFIG_DATA] set_tool_root(): 开始设置工具根目录，工具={repr(tool)}, 路径={repr(path)}")
        try:
            InputValidator.validate_tool_name(tool)
            if path:
                InputValidator.validate_path(path)
        except InputValidationError as e:
            logger.error(f"[CONFIG_DATA] set_tool_root(): 参数验证失败: {e}")
            return False
        result = self._config_manager.set_tool_root_config(tool, path)
        if result:
            logger.info(f"[CONFIG_DATA] set_tool_root(): 工具 {repr(tool)} 根目录设置成功")
        else:
            logger.error(f"[CONFIG_DATA] set_tool_root(): 工具 {repr(tool)} 根目录设置失败")
        return result

    def get_tool_root(self, tool: str) -> str:
        """获取工具根目录。"""
        logger.debug(f"[CONFIG_DATA] get_tool_root(): 开始获取工具根目录，工具={repr(tool)}")
        try:
            InputValidator.validate_tool_name(tool)
        except InputValidationError as e:
            logger.error(f"[CONFIG_DATA] get_tool_root(): 参数验证失败: {e}")
            return ""
        result = self._config_manager.get_tool_root(tool)
        logger.debug(f"[CONFIG_DATA] get_tool_root(): 工具 {repr(tool)} 根目录={repr(result)}")
        return result

    def add_tool_config(self, tool_name: str) -> bool:
        """添加新工具配置。"""
        logger.info(f"[CONFIG_DATA] add_tool_config(): 开始添加工具配置，工具={repr(tool_name)}")
        try:
            InputValidator.validate_tool_name(tool_name)
        except InputValidationError as e:
            logger.error(f"[CONFIG_DATA] add_tool_config(): 参数验证失败: {e}")
            return False
        result = self._config_manager.add_tool_config(tool_name)
        if result:
            logger.info(f"[CONFIG_DATA] add_tool_config(): 工具 {repr(tool_name)} 配置添加成功")
        else:
            logger.error(f"[CONFIG_DATA] add_tool_config(): 工具 {repr(tool_name)} 配置添加失败")
        return result

    def delete_tool_config(self, tool_name: str) -> bool:
        """删除工具配置。"""
        logger.info(f"[CONFIG_DATA] delete_tool_config(): 开始删除工具配置，工具={repr(tool_name)}")
        try:
            InputValidator.validate_tool_name(tool_name)
        except InputValidationError as e:
            logger.error(f"[CONFIG_DATA] delete_tool_config(): 参数验证失败: {e}")
            return False
        result = self._config_manager.delete_tool_config(tool_name)
        if result:
            logger.info(f"[CONFIG_DATA] delete_tool_config(): 工具 {repr(tool_name)} 配置删除成功")
        else:
            logger.error(f"[CONFIG_DATA] delete_tool_config(): 工具 {repr(tool_name)} 配置删除失败")
        return result

    def clear_cache(self) -> None:
        """清空缓存。"""
        logger.info("[CONFIG_DATA] clear_cache(): 开始清空缓存")
        self._config_manager.clear_cache()
        logger.info("[CONFIG_DATA] clear_cache(): 缓存清空成功")
