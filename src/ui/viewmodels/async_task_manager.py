"""
异步任务管理模块。

负责异步任务和线程的管理。
"""

from typing import Optional, Callable, Any, List, Dict
from PySide6.QtCore import QObject, Signal, Property, Slot, QRunnable, QThreadPool, QMetaObject, Qt, Q_ARG

from src.core.version_manager import VersionManager
from src.utils.logger import get_logger

logger = get_logger()


class RemoteVersionsLoader(QRunnable):
    """远程版本加载器（在后台线程执行）。"""
    
    def __init__(self, callback_obj, tool: str, version_manager: VersionManager):
        """
        初始化远程版本加载器。
        
        参数:
            callback_obj: 回调对象
            tool: 工具名称
            version_manager: 版本管理器实例
        """
        super().__init__()
        self.callback_obj = callback_obj
        self.tool = tool
        self.version_manager = version_manager
    
    def run(self):
        """在后台线程执行远程版本加载。"""
        logger.info(f"[ASYNC] RemoteVersionsLoader.run 开始执行: {self.tool}")
        try:
            if not self.tool:
                logger.warning("[ASYNC] 加载远程版本失败: 工具名称为空")
                return
                
            self._set_message(f"正在获取 {self.tool} 可用版本...")
            logger.debug(f"[ASYNC] 开始调用 version_manager.get_remote_versions({self.tool})")
            
            remote = self.version_manager.get_remote_versions(self.tool)
            logger.debug(f"[ASYNC] 成功获取 {len(remote)} 个原始版本数据")
            
            sorted_versions = self.version_manager.sort_versions_desc(remote)
            logger.debug(f"[ASYNC] 版本排序完成")
            
            versions = [
                {
                    "version": v["version"],
                    "downloadUrl": v.get("download_url", ""),
                    "lts": v.get("lts", False)
                }
                for v in sorted_versions[:100]
            ]
            
            grouped = self.version_manager.group_versions_by_major(remote)
            grouped_versions = []
            for group in grouped:
                group_data = {
                    "majorVersion": group["major_version"],
                    "hasLts": group.get("has_lts", False),
                    "versions": [
                        {
                            "version": v["version"],
                            "downloadUrl": v.get("download_url", ""),
                            "lts": v.get("lts", False)
                        }
                        for v in group["versions"]
                    ]
                }
                grouped_versions.append(group_data)
            
            logger.info(f"[ASYNC] 成功加载 {len(versions)} 个 {self.tool} 版本，分组数: {len(grouped_versions)}")
            
            self.callback_obj.remoteVersionsLoaded.emit(self.tool, versions, grouped_versions)
            logger.debug(f"[ASYNC] 已发送 remoteVersionsLoaded 信号")
        except Exception as e:
            error_msg = f"获取 {self.tool} 版本失败: {e}"
            logger.error(f"[ASYNC] {error_msg}", exc_info=True)
    
    def _set_message(self, msg: str):
        """设置消息。"""
        QMetaObject.invokeMethod(
            self.callback_obj,
            "_set_message",
            Qt.QueuedConnection,
            Q_ARG(str, msg)
        )


class Downloader(QRunnable):
    """下载器（在后台线程执行）。"""
    
    def __init__(self, callback_obj, tool: str, version: str, version_info: Optional[Dict[str, Any]], version_manager: VersionManager):
        """
        初始化下载器。
        
        参数:
            callback_obj: 回调对象
            tool: 工具名称
            version: 版本号
            version_info: 版本信息
            version_manager: 版本管理器实例
        """
        super().__init__()
        self.callback_obj = callback_obj
        self.tool = tool
        self.version = version
        self.version_info = version_info
        self.version_manager = version_manager
    
    def run(self):
        """在后台线程执行下载。"""
        logger.info(f"[ASYNC] Downloader.run 开始执行: {self.tool} {self.version}")
        success = False
        try:
            if not self.tool or not self.version:
                logger.warning("[ASYNC] 下载失败: 工具名称或版本为空")
                self._set_message(f"下载失败: 工具名称或版本为空")
                return
                
            self._set_message(f"正在下载 {self.tool} {self.version}...")
            self._set_download_progress(0)
            self._set_download_tool_name(self.tool)
            self._set_downloading_version(self.version)
            self._set_downloaded_bytes(0)
            self._set_total_bytes(0)
            logger.debug(f"[ASYNC] 开始调用 version_manager.download_version({self.tool}, {self.version})")
            
            def progress_callback(downloaded: int, total: int):
                progress = int(downloaded / total * 100) if total > 0 else 0
                self._set_download_progress(progress)
                self._set_downloaded_bytes(downloaded)
                self._set_total_bytes(total)
            
            def status_callback(msg: str):
                self._set_message(msg)
            
            success = self.version_manager.download_version(
                self.tool, self.version, progress_callback, status_callback, self.version_info
            )
            
            if success:
                logger.info(f"[ASYNC] 成功下载并安装 {self.tool} 版本 {self.version}")
                self._set_message(f"已成功安装 {self.tool} {self.version}")
            else:
                logger.warning(f"[ASYNC] {self.tool} 版本 {self.version} 下载失败")
                self._set_message(f"下载失败")
        except Exception as e:
            error_msg = f"下载 {self.tool} 版本 {self.version} 时发生异常: {e}"
            logger.error(f"[ASYNC] {error_msg}", exc_info=True)
            try:
                self._set_message(f"下载失败: {e}")
            except:
                logger.debug("[ASYNC] 无法设置错误消息，回调对象可能已删除")
        finally:
            try:
                self._set_download_complete()
            except:
                logger.debug("[ASYNC] 无法设置下载完成，回调对象可能已删除")
            try:
                if self.callback_obj:
                    self.callback_obj.downloadCompleted.emit(success)
                    logger.debug(f"[ASYNC] 已发送 downloadCompleted 信号，结果: {success}")
            except:
                logger.debug("[ASYNC] 无法发送 downloadCompleted 信号，回调对象可能已删除")
    
    def _set_message(self, msg: str):
        """设置消息。"""
        try:
            if self.callback_obj:
                QMetaObject.invokeMethod(
                    self.callback_obj,
                    "_set_message",
                    Qt.QueuedConnection,
                    Q_ARG(str, msg)
                )
        except RuntimeError:
            logger.debug("[ASYNC] 回调对象已删除，跳过设置消息")
        except Exception as e:
            logger.debug(f"[ASYNC] 设置消息时出错: {e}")
    
    def _set_download_progress(self, progress: int):
        """设置下载进度。"""
        try:
            if self.callback_obj:
                QMetaObject.invokeMethod(
                    self.callback_obj,
                    "set_download_progress",
                    Qt.QueuedConnection,
                    Q_ARG(int, progress)
                )
        except RuntimeError:
            logger.debug("[ASYNC] 回调对象已删除，跳过设置下载进度")
        except Exception as e:
            logger.debug(f"[ASYNC] 设置下载进度时出错: {e}")
    
    def _set_download_complete(self):
        """设置下载完成。"""
        try:
            if self.callback_obj:
                QMetaObject.invokeMethod(
                    self.callback_obj,
                    "set_download_complete",
                    Qt.QueuedConnection
                )
        except RuntimeError:
            logger.debug("[ASYNC] 回调对象已删除，跳过设置下载完成")
        except Exception as e:
            logger.debug(f"[ASYNC] 设置下载完成时出错: {e}")
    
    def _set_download_tool_name(self, tool_name: str):
        """设置下载工具名称。"""
        try:
            if self.callback_obj:
                QMetaObject.invokeMethod(
                    self.callback_obj,
                    "set_download_tool_name",
                    Qt.QueuedConnection,
                    Q_ARG(str, tool_name)
                )
        except RuntimeError:
            logger.debug("[ASYNC] 回调对象已删除，跳过设置工具名称")
        except Exception as e:
            logger.debug(f"[ASYNC] 设置工具名称时出错: {e}")
    
    def _set_downloading_version(self, version: str):
        """设置正在下载的版本。"""
        try:
            if self.callback_obj:
                QMetaObject.invokeMethod(
                    self.callback_obj,
                    "set_downloading_version",
                    Qt.QueuedConnection,
                    Q_ARG(str, version)
                )
        except RuntimeError:
            logger.debug("[ASYNC] 回调对象已删除，跳过设置版本")
        except Exception as e:
            logger.debug(f"[ASYNC] 设置版本时出错: {e}")
    
    def _set_downloaded_bytes(self, bytes: int):
        """设置已下载字节数。"""
        try:
            if self.callback_obj:
                QMetaObject.invokeMethod(
                    self.callback_obj,
                    "set_downloaded_bytes",
                    Qt.QueuedConnection,
                    Q_ARG(int, bytes)
                )
        except RuntimeError:
            logger.debug("[ASYNC] 回调对象已删除，跳过设置已下载字节数")
        except Exception as e:
            logger.debug(f"[ASYNC] 设置已下载字节数时出错: {e}")
    
    def _set_total_bytes(self, bytes: int):
        """设置总字节数。"""
        try:
            if self.callback_obj:
                QMetaObject.invokeMethod(
                    self.callback_obj,
                    "set_total_bytes",
                    Qt.QueuedConnection,
                    Q_ARG(int, bytes)
                )
        except RuntimeError:
            logger.debug("[ASYNC] 回调对象已删除，跳过设置总字节数")
        except Exception as e:
            logger.debug(f"[ASYNC] 设置总字节数时出错: {e}")


class AsyncTaskManager(QObject):
    """
    异步任务管理器类。
    
    负责异步任务和线程的管理。
    """

    messageChanged = Signal()
    downloadProgressChanged = Signal()
    downloadInProgressChanged = Signal()
    remoteVersionsLoaded = Signal(str, list, list)
    downloadCompleted = Signal(bool)
    downloadToolNameChanged = Signal()
    downloadingVersionChanged = Signal()
    downloadedBytesChanged = Signal()
    totalBytesChanged = Signal()

    def __init__(self, version_manager: VersionManager, parent=None):
        """
        初始化异步任务管理器。
        
        参数:
            version_manager: 版本管理器实例
            parent: 父对象
        """
        super().__init__(parent)
        logger.info("[ASYNC] 初始化 AsyncTaskManager")
        self._version_manager = version_manager
        self._message: str = ""
        self._download_progress: int = 0
        self._download_in_progress: bool = False
        self._download_tool_name: str = ""
        self._downloading_version: str = ""
        self._downloaded_bytes: int = 0
        self._total_bytes: int = 0
        self._thread_pool = QThreadPool()
        self._thread_pool.setMaxThreadCount(4)
        self._remote_versions_loading: bool = False
        logger.debug(f"[ASYNC] 线程池最大线程数设置为 4")

    @Property(str, notify=messageChanged)
    def message(self) -> str:
        """获取消息内容。"""
        return self._message

    @Property(int, notify=downloadProgressChanged)
    def downloadProgress(self) -> int:
        """获取下载进度。"""
        return self._download_progress

    @Property(bool, notify=downloadInProgressChanged)
    def downloadInProgress(self) -> bool:
        """获取下载是否正在进行。"""
        return self._download_in_progress

    @Property(str, notify=downloadToolNameChanged)
    def downloadToolName(self) -> str:
        """获取下载工具名称。"""
        return self._download_tool_name

    @Property(str, notify=downloadingVersionChanged)
    def downloadingVersion(self) -> str:
        """获取正在下载的版本。"""
        return self._downloading_version

    @Property(int, notify=downloadedBytesChanged)
    def downloadedBytes(self) -> int:
        """获取已下载字节数。"""
        return self._downloaded_bytes

    @Property(int, notify=totalBytesChanged)
    def totalBytes(self) -> int:
        """获取总字节数。"""
        return self._total_bytes

    @Slot(str)
    def _set_message(self, msg: str):
        """设置消息内容。"""
        self._message = msg
        self.messageChanged.emit()
        logger.info(f"[ASYNC] {msg}")

    @Slot(int)
    def set_download_progress(self, progress: int):
        """设置下载进度。"""
        clamped_progress = max(0, min(100, progress))
        if clamped_progress != self._download_progress:
            logger.debug(f"[ASYNC] 更新下载进度: {self._download_progress}% -> {clamped_progress}%")
            self._download_progress = clamped_progress
            self.downloadProgressChanged.emit()

    @Slot(str)
    def set_download_tool_name(self, tool_name: str):
        """设置下载工具名称。"""
        if tool_name != self._download_tool_name:
            self._download_tool_name = tool_name
            self.downloadToolNameChanged.emit()

    @Slot(str)
    def set_downloading_version(self, version: str):
        """设置正在下载的版本。"""
        if version != self._downloading_version:
            self._downloading_version = version
            self.downloadingVersionChanged.emit()

    @Slot(int)
    def set_downloaded_bytes(self, bytes: int):
        """设置已下载字节数。"""
        if bytes != self._downloaded_bytes:
            self._downloaded_bytes = bytes
            self.downloadedBytesChanged.emit()

    @Slot(int)
    def set_total_bytes(self, bytes: int):
        """设置总字节数。"""
        if bytes != self._total_bytes:
            self._total_bytes = bytes
            self.totalBytesChanged.emit()

    @Slot()
    def set_download_complete(self):
        """设置下载完成。"""
        if self._download_in_progress:
            logger.debug("[ASYNC] 设置 downloadInProgress 为 false")
            self._download_in_progress = False
            self.downloadInProgressChanged.emit()

    def load_remote_versions_async(self, tool: str):
        """异步加载远程可用版本列表。"""
        if not tool:
            logger.warning("[ASYNC] load_remote_versions_async: 工具名称为空，跳过加载")
            return
        
        logger.info(f"[ASYNC] 启动异步加载 {tool} 的远程版本任务")
        runnable = RemoteVersionsLoader(self, tool, self._version_manager)
        self._thread_pool.start(runnable)
        logger.debug(f"[ASYNC] 已将 {tool} 的远程版本加载任务提交到线程池")

    @Slot(int, result=str)
    def format_file_size(self, bytes: int) -> str:
        """格式化文件大小。"""
        if bytes <= 0:
            return "0 B"
        
        kb = 1024
        mb = kb * 1024
        gb = mb * 1024
        
        if bytes < kb:
            return f"{bytes} B"
        elif bytes < mb:
            return f"{bytes / kb:.2f} KB"
        elif bytes < gb:
            return f"{bytes / mb:.2f} MB"
        else:
            return f"{bytes / gb:.2f} GB"

    def download_version(
        self,
        tool: str,
        version: str,
        version_info: Optional[Dict[str, Any]] = None
    ):
        """异步下载并安装指定版本。"""
        logger.info(f"[ASYNC] 开始异步下载 {tool} 版本 {version}")
        self._download_progress = 0
        self.downloadProgressChanged.emit()
        self._download_in_progress = True
        self.downloadInProgressChanged.emit()
        self._download_tool_name = ""
        self.downloadToolNameChanged.emit()
        self._downloading_version = ""
        self.downloadingVersionChanged.emit()
        self._downloaded_bytes = 0
        self.downloadedBytesChanged.emit()
        self._total_bytes = 0
        self.totalBytesChanged.emit()
        logger.debug("[ASYNC] 重置下载进度为 0%，设置 downloadInProgress 为 true，重置下载相关属性")
        
        runnable = Downloader(self, tool, version, version_info, self._version_manager)
        self._thread_pool.start(runnable)
        logger.debug(f"[ASYNC] 已将 {tool} 版本 {version} 的下载任务提交到线程池")
