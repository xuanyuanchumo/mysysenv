"""
图形界面后端模块。

提供 QML 与 Python 之间的交互桥接功能。
使用 ViewModel 模式，将具体工作委托给各个专用 ViewModel。
"""

import sys
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QObject, Signal, Property, Slot, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from src.core.config_manager import ConfigManager
from src.core.env_manager import EnvManager
from src.core.version_manager import VersionManager
from src.utils.permission_manager import is_admin
from src.utils.logger import get_logger
from src.ui.viewmodels import (
    ToolDataProvider,
    ConfigDataProvider,
    AsyncTaskManager,
    LoggerBridge,
)

logger = get_logger()


class Backend(QObject):
    """
    QML 后端类（简化版）。
    
    作为最小 UI 桥接，将具体工作委托给各个专用 ViewModel。
    """
    
    toolsChanged = Signal()
    currentToolChanged = Signal()
    installedVersionsChanged = Signal()
    remoteVersionsChanged = Signal()
    groupedRemoteVersionsChanged = Signal()
    currentVersionChanged = Signal()
    messageChanged = Signal()
    downloadProgressChanged = Signal()
    downloadInProgressChanged = Signal()
    configJsonChanged = Signal()
    isAdminChanged = Signal()
    remoteVersionsLoadingChanged = Signal()
    downloadToolNameChanged = Signal()
    downloadingVersionChanged = Signal()
    downloadedBytesChanged = Signal()
    totalBytesChanged = Signal()

    def __init__(self, parent=None):
        """初始化后端对象。"""
        super().__init__(parent)
        self._log = get_logger()
        self._log.info("初始化 Backend 开始")
        
        self._config_manager = ConfigManager()
        self._env_manager = EnvManager()
        self._version_manager = VersionManager(self._config_manager, self._env_manager)
        
        self._tool_data = ToolDataProvider(self._config_manager, self._version_manager, self)
        self._version_manager.local_manager._version_manager = self._version_manager
        self._config_data = ConfigDataProvider(self._config_manager, self)
        self._async_task = AsyncTaskManager(self._version_manager, self)
        self._logger = LoggerBridge(self)
        
        self._is_admin: bool = is_admin()
        self._log.debug(f"管理员权限状态: {self._is_admin}")
        
        self._connect_signals()
        self._tool_data._load_tools()
        if self._tool_data.tools:
            first_tool = self._tool_data.tools[0]["name"]
            self._tool_data.currentTool = first_tool
            self._tool_data.load_tool_data()
        self._log.info("Backend 初始化完成")

    def _connect_signals(self):
        """连接各个 ViewModel 的信号到本类的信号。"""
        self._log.debug("连接信号开始")
        self._tool_data.toolsChanged.connect(self.toolsChanged)
        self._tool_data.currentToolChanged.connect(self.currentToolChanged)
        self._tool_data.installedVersionsChanged.connect(self.installedVersionsChanged)
        self._tool_data.remoteVersionsChanged.connect(self.remoteVersionsChanged)
        self._tool_data.groupedRemoteVersionsChanged.connect(self.groupedRemoteVersionsChanged)
        self._tool_data.currentVersionChanged.connect(self.currentVersionChanged)
        self._tool_data.remoteVersionsLoadingChanged.connect(self.remoteVersionsLoadingChanged)
        
        self._config_data.configJsonChanged.connect(self.configJsonChanged)
        
        self._async_task.messageChanged.connect(self.messageChanged)
        self._async_task.downloadProgressChanged.connect(self.downloadProgressChanged)
        self._async_task.downloadInProgressChanged.connect(self.downloadInProgressChanged)
        self._async_task.downloadToolNameChanged.connect(self.downloadToolNameChanged)
        self._async_task.downloadingVersionChanged.connect(self.downloadingVersionChanged)
        self._async_task.downloadedBytesChanged.connect(self.downloadedBytesChanged)
        self._async_task.totalBytesChanged.connect(self.totalBytesChanged)
        self._async_task.remoteVersionsLoaded.connect(self._on_remote_versions_loaded)
        self._async_task.downloadCompleted.connect(self._on_download_completed)
        self._log.debug("信号连接完成")

    @Property(list, notify=toolsChanged)
    def tools(self):
        """获取工具列表。"""
        return self._tool_data.tools

    @Property(str, notify=currentToolChanged)
    def currentTool(self) -> str:
        """获取当前选中的工具。"""
        return self._tool_data.currentTool

    @currentTool.setter
    def currentTool(self, value: str):
        """设置当前选中的工具。"""
        old_value = self._tool_data.currentTool
        self._log.debug(f"设置当前工具: 旧值={old_value}, 新值={value}")
        self._tool_data.currentTool = value
        if old_value != value:
            self._load_tool_data()

    @Property(list, notify=installedVersionsChanged)
    def installedVersions(self):
        """获取已安装版本列表。"""
        return self._tool_data.installedVersions

    @Property(list, notify=remoteVersionsChanged)
    def remoteVersions(self):
        """获取远程可用版本列表。"""
        return self._tool_data.remoteVersions

    @Property(list, notify=groupedRemoteVersionsChanged)
    def groupedRemoteVersions(self):
        """获取分组后的远程版本列表。"""
        return self._tool_data.groupedRemoteVersions

    @Property(str, notify=currentVersionChanged)
    def currentVersion(self) -> str:
        """获取当前使用的版本。"""
        return self._tool_data.currentVersion

    @Property(str, notify=messageChanged)
    def message(self) -> str:
        """获取消息内容。"""
        return self._async_task.message

    @Property(int, notify=downloadProgressChanged)
    def downloadProgress(self) -> int:
        """获取下载进度。"""
        return self._async_task.downloadProgress

    @Property(bool, notify=downloadInProgressChanged)
    def downloadInProgress(self) -> bool:
        """获取下载是否正在进行。"""
        return self._async_task.downloadInProgress

    @Property(str, notify=configJsonChanged)
    def configJson(self) -> str:
        """获取配置 JSON 字符串。"""
        return self._config_data.configJson

    @configJson.setter
    def configJson(self, value: str):
        """设置配置 JSON 字符串。"""
        self._config_data.configJson = value

    @Property(bool, notify=isAdminChanged)
    def isAdmin(self) -> bool:
        """检查是否以管理员权限运行。"""
        return self._is_admin

    @Property(bool, notify=remoteVersionsLoadingChanged)
    def remoteVersionsLoading(self) -> bool:
        """获取远程版本加载状态。"""
        return self._tool_data.remoteVersionsLoading

    @remoteVersionsLoading.setter
    def remoteVersionsLoading(self, value: bool):
        """设置远程版本加载状态。"""
        self._tool_data.remoteVersionsLoading = value

    @Property(str, notify=downloadToolNameChanged)
    def downloadToolName(self) -> str:
        """获取下载工具名称。"""
        return self._async_task.downloadToolName

    @Property(str, notify=downloadingVersionChanged)
    def downloadingVersion(self) -> str:
        """获取正在下载的版本。"""
        return self._async_task.downloadingVersion

    @Property(int, notify=downloadedBytesChanged)
    def downloadedBytes(self) -> int:
        """获取已下载字节数。"""
        return self._async_task.downloadedBytes

    @Property(int, notify=totalBytesChanged)
    def totalBytes(self) -> int:
        """获取总字节数。"""
        return self._async_task.totalBytes

    @Slot(int, result=str)
    def format_file_size(self, bytes: int) -> str:
        """格式化文件大小。"""
        return self._async_task.format_file_size(bytes)

    @Slot(str)
    def _set_message(self, msg: str):
        """设置消息内容。"""
        self._async_task._set_message(msg)

    @Slot(str)
    def logInfo(self, message: str):
        """记录信息级日志（QML 槽函数）。"""
        self._logger.logInfo(message)

    @Slot(str)
    def logDebug(self, message: str):
        """记录调试级日志（QML 槽函数）。"""
        self._logger.logDebug(message)

    @Slot(str)
    def logWarning(self, message: str):
        """记录警告级日志（QML 槽函数）。"""
        self._logger.logWarning(message)

    @Slot(str)
    def logError(self, message: str):
        """记录错误级日志（QML 槽函数）。"""
        self._logger.logError(message)

    def _load_tool_data(self):
        """加载当前工具的数据。"""
        self._log.debug(f"加载工具数据开始: 当前工具={self._tool_data.currentTool}")
        self._tool_data.load_tool_data()
        self._load_remote_versions_async()
        self._log.debug("工具数据加载完成")

    @Slot(str, str, bool)
    def lockVersion(self, tool: str, version: str, locked: bool):
        """锁定或解锁指定版本（QML 槽函数）。"""
        self._log.info(f"{'锁定' if locked else '解锁'}版本请求: 工具={tool}, 版本={version}")
        if not tool or not version:
            self._log.warning("锁定/解锁版本失败: 工具或版本为空")
            return
        self._set_message(f"正在{'锁定' if locked else '解锁'} {tool} 版本 {version}...")
        if self._version_manager.lock_version(tool, version, locked):
            action = "锁定" if locked else "解锁"
            self._log.info(f"版本{action}成功: 工具={tool}, 版本={version}")
            self._set_message(f"已{action} {tool} 版本 {version}")
            self._load_tool_data()
        else:
            self._log.error(f"版本{action}失败: 工具={tool}, 版本={version}")
            self._set_message(f"{'锁定' if locked else '解锁'}版本失败")

    @Slot()
    def loadRemoteVersions(self):
        """加载远程版本列表（QML 槽函数）。"""
        self._log.debug("加载远程版本列表请求")
        self._load_remote_versions_async()
    
    @Slot()
    def loadInstalledVersions(self):
        """刷新已安装版本列表（QML 槽函数）。"""
        self._log.debug("刷新已安装版本列表请求")
        self._load_tool_data()

    def _load_remote_versions_async(self):
        """异步加载远程可用版本列表。"""
        if not self._tool_data.currentTool:
            self._log.warning("异步加载远程版本失败: 当前工具为空")
            return
        self._log.info(f"异步加载远程版本开始: 工具={self._tool_data.currentTool}")
        self._tool_data.remoteVersionsLoading = True
        self._async_task.load_remote_versions_async(self._tool_data.currentTool)

    @Slot(str, list, list)
    def _on_remote_versions_loaded(self, tool, versions, grouped_versions):
        """远程版本加载完成后的回调方法。"""
        self._log.info(f"远程版本加载完成: 工具={tool}, 版本数量={len(versions)}")
        self._tool_data.update_remote_versions(tool, versions, grouped_versions)
        self._set_message(f"已获取 {len(versions)} 个可用版本")
        self._tool_data.remoteVersionsLoading = False

    @Slot(str)
    def switchVersion(self, version: str):
        """切换到指定版本（QML 槽函数）。"""
        self._log.info(f"切换版本请求: 工具={self._tool_data.currentTool}, 版本={version}")
        if not self._tool_data.currentTool or not version:
            self._log.warning("切换版本失败: 工具或版本为空")
            return
        self._set_message(f"正在切换 {self._tool_data.currentTool} 到版本 {version}...")
        if self._version_manager.switch_version(self._tool_data.currentTool, version):
            self._log.info(f"版本切换成功: 工具={self._tool_data.currentTool}, 版本={version}")
            self._set_message(f"已切换 {self._tool_data.currentTool} 到版本 {version}")
            self._tool_data.load_tool_data()
            self.currentVersionChanged.emit()
            self.installedVersionsChanged.emit()
        else:
            self._log.error(f"版本切换失败: 工具={self._tool_data.currentTool}, 版本={version}")
            self._set_message(f"切换版本失败")

    @Slot(bool)
    def _on_download_completed(self, success: bool):
        """下载完成后的回调方法。"""
        self._log.info(f"下载完成: 成功={success}")
        if success:
            self._log.info("版本下载安装成功")
            self._load_tool_data()
        else:
            self._log.error("版本下载失败")
    
    @Slot(str)
    def downloadVersion(self, version: str):
        """下载并安装指定版本（QML 槽函数）。"""
        self._log.info(f"下载版本请求: 工具={self._tool_data.currentTool}, 版本={version}")
        if not self._tool_data.currentTool or not version:
            self._log.warning("下载版本失败: 工具或版本为空")
            return
        self._set_message(f"正在下载 {self._tool_data.currentTool} {version}...")
        self._async_task.download_version(self._tool_data.currentTool, version)

    @Slot(str)
    def deleteVersion(self, version: str):
        """删除指定版本（QML 槽函数）。"""
        self._log.info(f"删除版本请求: 工具={self._tool_data.currentTool}, 版本={version}")
        if not self._tool_data.currentTool or not version:
            self._log.warning("删除版本失败: 工具或版本为空")
            return
        if version == self._tool_data.currentVersion:
            self._log.warning("删除版本失败: 无法删除当前使用的版本")
            self._set_message("无法删除当前使用的版本")
            return
        
        self._set_message(f"正在删除 {self._tool_data.currentTool} {version}...")
        if self._version_manager.delete_version(self._tool_data.currentTool, version):
            self._log.info(f"版本删除成功: 工具={self._tool_data.currentTool}, 版本={version}")
            self._set_message(f"已删除 {self._tool_data.currentTool} {version}")
            self._load_tool_data()
        else:
            self._log.error(f"版本删除失败: 工具={self._tool_data.currentTool}, 版本={version}")
            self._set_message("删除失败")

    @Slot()
    def loadConfig(self):
        """加载配置（QML 槽函数）。"""
        self._log.debug("加载配置请求")
        self._config_data.load_config()
        self._log.info("配置加载完成")

    @Slot(str)
    def loadToolSpecificConfig(self, tool_name: str):
        """加载工具特定配置（QML 槽函数）。"""
        self._log.debug(f"加载工具特定配置请求: 工具={tool_name}")
        self._config_data.load_tool_specific_config(tool_name)
        self._log.info(f"工具特定配置加载完成: 工具={tool_name}")

    @Slot(str, str, result=bool)
    def saveToolSpecificConfig(self, tool_name: str, config_json: str) -> bool:
        """保存工具特定配置（QML 槽函数）。"""
        self._log.info(f"保存工具特定配置请求: 工具={tool_name}")
        result = self._config_data.save_tool_specific_config(tool_name, config_json)
        if result:
            self._log.info(f"工具特定配置保存成功: 工具={tool_name}")
            self._set_message(f"{tool_name} 配置保存成功")
            self._tool_data.refresh_tools()
        else:
            self._log.error(f"工具特定配置保存失败: 工具={tool_name}")
            self._set_message("配置保存失败")
        return result

    @Slot(str, result=bool)
    def saveConfig(self, config_json: str) -> bool:
        """保存配置（QML 槽函数）。"""
        self._log.info("保存配置请求")
        result = self._config_data.save_config(config_json)
        if result:
            self._log.info("配置保存成功")
            self._set_message("配置保存成功")
            self._tool_data.refresh_tools()
        else:
            self._log.error("配置保存失败")
            self._set_message("配置保存失败")
        return result

    @Slot(str, str)
    def setToolRoot(self, tool: str, path: str):
        """设置工具根目录（QML 槽函数）。"""
        self._log.info(f"设置工具根目录请求: 工具={tool}, 路径={path}")
        self._config_data.set_tool_root(tool, path)
        self._tool_data.refresh_tools()
        self._set_message(f"已设置 {tool} 根目录为 {path}")

    @Slot(str, result=str)
    def getToolRoot(self, tool: str) -> str:
        """获取工具根目录（QML 槽函数）。"""
        self._log.debug(f"获取工具根目录请求: 工具={tool}")
        return self._config_data.get_tool_root(tool)

    @Slot()
    def resetToDefaultConfig(self):
        """重置配置为默认配置（QML 槽函数）。"""
        self._log.info("重置配置为默认配置请求")
        self._config_data.reset_to_default()
        self._tool_data.refresh_tools()
        self._tool_data.reset_current_tool()
        self._log.info("配置已重置为默认配置")
        self._set_message("已恢复默认配置")

    @Slot(str, result=bool)
    def addToolConfig(self, tool_name: str) -> bool:
        """添加新工具配置（QML 槽函数）。"""
        self._log.info(f"添加工具配置请求: 工具={tool_name}")
        if not tool_name or not tool_name.strip():
            self._log.warning("添加工具配置失败: 工具名称为空")
            self._set_message("工具名称不能为空")
            return False
        
        tool_name = tool_name.strip().lower()
        if self._config_data.add_tool_config(tool_name):
            self._log.info(f"工具配置添加成功: 工具={tool_name}")
            self._tool_data.refresh_tools()
            self._config_data.load_config()
            self._set_message(f"已添加工具配置: {tool_name}")
            return True
        else:
            self._log.warning(f"工具配置添加失败: 工具={tool_name} 已存在")
            self._set_message(f"工具 {tool_name} 已存在")
            return False

    @Slot(str, result=bool)
    def deleteToolConfig(self, tool_name: str) -> bool:
        """删除工具配置（QML 槽函数）。"""
        self._log.info(f"删除工具配置请求: 工具={tool_name}")
        if not tool_name or not tool_name.strip():
            self._log.warning("删除工具配置失败: 工具名称为空")
            self._set_message("工具名称不能为空")
            return False
        
        tool_name = tool_name.strip().lower()
        if self._config_data.delete_tool_config(tool_name):
            self._log.info(f"工具配置删除成功: 工具={tool_name}")
            self._tool_data.refresh_tools()
            self._tool_data.reset_current_tool()
            self._config_data.load_config()
            self._set_message(f"已删除工具配置: {tool_name}")
            return True
        else:
            self._log.error(f"工具配置删除失败: 工具={tool_name}")
            self._set_message("删除工具配置失败")
            return False

    @Slot()
    def clearCache(self):
        """清空缓存（QML 槽函数）。"""
        self._log.info("清空缓存请求")
        self._config_data.clear_cache()
        self._log.info("缓存已清空")
        self._set_message("缓存已清空")

    @Slot(str, result=str)
    def getToolConfigJson(self, tool_name: str) -> str:
        """获取 settings 字段的配置 JSON 字符串（QML 槽函数）。"""
        self._log.debug(f"获取工具配置 JSON 请求: 工具={tool_name}")
        return self._config_data.get_tool_config_json()

    def _set_remote_versions_loading(self, value: bool):
        """设置远程版本加载状态（内部使用）。"""
        self._log.debug(f"设置远程版本加载状态: {value}")
        self._tool_data.remoteVersionsLoading = value


def run_gui():
    """
    启动图形用户界面。
    
    返回:
        退出码
    """
    app = QApplication(sys.argv)
    app.setApplicationName("Mysysenv")
    app.setOrganizationName("Mysysenv")
    engine = QQmlApplicationEngine()
    backend = Backend()
    engine.rootContext().setContextProperty("backend", backend)
    qml_dir = Path(__file__).parent / "qml"
    main_qml = qml_dir / "Main.qml"
    if main_qml.exists():
        engine.load(QUrl.fromLocalFile(str(main_qml)))
    else:
        from PySide6.QtQuick import QQuickView
        from PySide6.QtCore import QRect
        view = QQuickView()
        view.setTitle("Mysysenv - 系统环境管理器")
        view.setResizeMode(QQuickView.SizeRootObjectToView)
        view.setWidth(1024)
        view.setHeight(768)
        view.show()
    if not engine.rootObjects():
        sys.exit(-1)
    
    sys.exit(app.exec())
