"""
工具数据提供模块。

负责工具和版本数据的管理，包括工具列表、已安装版本、远程版本等。
"""

from typing import List, Dict, Any, Optional
from PySide6.QtCore import QObject, Signal, Property

from src.core.config_manager import ConfigManager
from src.core.version_manager import VersionManager
from src.utils.logger import get_logger

logger = get_logger()


class ToolDataProvider(QObject):
    """
    工具数据提供类。
    
    负责工具和版本数据的管理，包括工具列表、已安装版本、远程版本等。
    """

    toolsChanged = Signal()
    currentToolChanged = Signal()
    installedVersionsChanged = Signal()
    remoteVersionsChanged = Signal()
    groupedRemoteVersionsChanged = Signal()
    currentVersionChanged = Signal()
    remoteVersionsLoadingChanged = Signal()

    def __init__(
        self,
        config_manager: ConfigManager,
        version_manager: VersionManager,
        parent=None
    ):
        """
        初始化工具数据提供器。
        
        参数:
            config_manager: 配置管理器实例
            version_manager: 版本管理器实例
            parent: 父对象
        """
        logger.info("[TOOL_DATA] 初始化 ToolDataProvider")
        super().__init__(parent)
        self._config_manager = config_manager
        self._version_manager = version_manager
        self._tools: List[Dict[str, str]] = []
        self._current_tool: str = ""
        self._installed_versions: List[Dict[str, str]] = []
        self._remote_versions: List[Dict[str, str]] = []
        self._grouped_remote_versions: List[Dict[str, Any]] = []
        self._current_version: str = ""
        self._remote_versions_loading: bool = False
        logger.debug("[TOOL_DATA] 开始加载工具列表")
        self._load_tools()
        logger.info("[TOOL_DATA] ToolDataProvider 初始化完成")

    def _load_tools(self):
        """加载工具列表。"""
        tool_templates = self._config_manager.get_tool_templates()
        logger.info(f"[TOOL_DATA] 加载工具模板，数量: {len(tool_templates)}")
        
        self._tools = [{"name": name, "path": template.get("tool_root", "")} 
                       for name, template in tool_templates.items()]
        
        logger.info(f"[TOOL_DATA] 构建的工具列表: {self._tools}")
        self.toolsChanged.emit()

    @Property(list, notify=toolsChanged)
    def tools(self) -> List[Dict[str, str]]:
        """获取工具列表。"""
        return self._tools

    @Property(str, notify=currentToolChanged)
    def currentTool(self) -> str:
        """获取当前选中的工具。"""
        return self._current_tool

    @currentTool.setter
    def currentTool(self, value: str):
        """设置当前选中的工具。"""
        if self._current_tool != value:
            old_value = self._current_tool
            self._current_tool = value
            logger.info(f"[TOOL_DATA] currentTool 变更: 旧值={repr(old_value)}, 新值={repr(value)}")
            self.currentToolChanged.emit()

    @Property(list, notify=installedVersionsChanged)
    def installedVersions(self) -> List[Dict[str, str]]:
        """获取已安装版本列表。"""
        return self._installed_versions

    @Property(list, notify=remoteVersionsChanged)
    def remoteVersions(self) -> List[Dict[str, str]]:
        """获取远程可用版本列表。"""
        return self._remote_versions

    @Property(list, notify=groupedRemoteVersionsChanged)
    def groupedRemoteVersions(self) -> List[Dict[str, Any]]:
        """获取分组后的远程版本列表。"""
        return self._grouped_remote_versions

    @Property(str, notify=currentVersionChanged)
    def currentVersion(self) -> str:
        """获取当前使用的版本。"""
        return self._current_version

    @currentVersion.setter
    def currentVersion(self, value: str):
        """设置当前使用的版本。"""
        if self._current_version != value:
            old_value = self._current_version
            self._current_version = value
            logger.info(f"[TOOL_DATA] currentVersion 变更: 旧值={repr(old_value)}, 新值={repr(value)}")
            self.currentVersionChanged.emit()

    @Property(bool, notify=remoteVersionsLoadingChanged)
    def remoteVersionsLoading(self) -> bool:
        """获取远程版本加载状态。"""
        return self._remote_versions_loading

    @remoteVersionsLoading.setter
    def remoteVersionsLoading(self, value: bool):
        """设置远程版本加载状态。"""
        if self._remote_versions_loading != value:
            old_value = self._remote_versions_loading
            self._remote_versions_loading = value
            logger.info(f"[TOOL_DATA] remoteVersionsLoading 变更: 旧值={old_value}, 新值={value}")
            self.remoteVersionsLoadingChanged.emit()

    def load_tool_data(self):
        """加载当前工具的数据。"""
        if not self._current_tool:
            logger.debug("[TOOL_DATA] load_tool_data(): 当前工具为空，跳过加载")
            return
        logger.info(f"[TOOL_DATA] load_tool_data(): 开始加载工具数据，工具={repr(self._current_tool)}")
        self._version_manager.check_and_update_system_version(self._current_tool)
        installed = self._version_manager.scan_local_versions(self._current_tool)
        self._installed_versions = [
            {
                "version": v["version"], 
                "path": v["path"],
                "locked": v.get("locked", False),
                "is_system": v.get("is_system", False)
            }
            for v in installed
        ]
        self.installedVersionsChanged.emit()
        logger.info(f"[TOOL_DATA] load_tool_data(): 已安装版本数量={len(self._installed_versions)}")
        current = self._version_manager.get_current_version(self._current_tool)
        self._current_version = current or ""
        self.currentVersionChanged.emit()
        logger.info(f"[TOOL_DATA] load_tool_data(): 当前版本={repr(self._current_version)}")

    def update_remote_versions(self, tool: str, versions: List[Dict[str, Any]], grouped_versions: List[Dict[str, Any]]):
        """更新远程版本数据。"""
        logger.info(f"[TOOL_DATA] update_remote_versions(): 开始更新，工具={repr(tool)}, 远程版本数量={len(versions)}, 分组数量={len(grouped_versions)}")
        if tool != self._current_tool:
            logger.debug(f"[TOOL_DATA] update_remote_versions(): 工具 {repr(tool)} 与当前工具 {repr(self._current_tool)} 不匹配，忽略")
            return
        
        self._remote_versions = versions
        logger.debug(f"[TOOL_DATA] update_remote_versions(): 更新 remoteVersions，数量={len(versions)}")
        self.remoteVersionsChanged.emit()

        installed_version_set = set()
        for v in self._installed_versions:
            installed_version_set.add(v.get("version", ""))

        for version in grouped_versions:
            for v in version.get("versions", []):
                v["isInstalled"] = v.get("version", "") in installed_version_set

        self._grouped_remote_versions = grouped_versions
        logger.debug(f"[TOOL_DATA] update_remote_versions(): 更新 groupedRemoteVersions，数量={len(grouped_versions)}")
        self.groupedRemoteVersionsChanged.emit()
        logger.info(f"[TOOL_DATA] update_remote_versions(): 更新完成")

    def refresh_tools(self):
        """刷新工具列表。"""
        logger.info("[TOOL_DATA] refresh_tools(): 开始刷新工具列表")
        self._load_tools()
        logger.info("[TOOL_DATA] refresh_tools(): 刷新完成")

    def reset_current_tool(self):
        """重置当前工具为空。"""
        logger.info(f"[TOOL_DATA] reset_current_tool(): 重置当前工具，旧值={repr(self._current_tool)}")
        self._current_tool = ""
        self.currentToolChanged.emit()
        logger.info("[TOOL_DATA] reset_current_tool(): 重置完成")
