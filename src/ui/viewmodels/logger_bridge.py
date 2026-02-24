"""
日志桥接模块。

提供 QML 与日志系统之间的桥接功能。
"""

from PySide6.QtCore import QObject, Slot

from src.utils.logger import get_logger

logger = get_logger()


class LoggerBridge(QObject):
    """
    日志桥接类。
    
    提供 QML 与日志系统之间的桥接功能。
    """

    def __init__(self, parent=None):
        """初始化日志桥接器。"""
        super().__init__(parent)

    @Slot(str)
    def logInfo(self, message: str):
        """
        记录信息级日志（QML 槽函数）。
        
        参数:
            message: 日志消息
        """
        logger.info(f"[QML] {message}")

    @Slot(str)
    def logDebug(self, message: str):
        """
        记录调试级日志（QML 槽函数）。
        
        参数:
            message: 日志消息
        """
        logger.debug(f"[QML] {message}")

    @Slot(str)
    def logWarning(self, message: str):
        """
        记录警告级日志（QML 槽函数）。
        
        参数:
            message: 日志消息
        """
        logger.warning(f"[QML] {message}")

    @Slot(str)
    def logError(self, message: str):
        """
        记录错误级日志（QML 槽函数）。
        
        参数:
            message: 日志消息
        """
        logger.error(f"[QML] {message}")
