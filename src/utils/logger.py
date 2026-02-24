"""
日志模块。

提供应用程序日志的配置和管理功能。
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

_logger: Optional[logging.Logger] = None


def get_app_dir() -> Path:
    """
    获取应用程序目录路径。
    
    返回:
        应用程序所在目录的 Path 对象
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent


APP_DIR = get_app_dir()
LOG_DIR = APP_DIR / "logs"
LOG_FILE = LOG_DIR / "mysysenv.log"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(module)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 5


def setup_logger(
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_to_console: bool = True,
    log_dir: Optional[Path] = None,
    max_bytes: int = MAX_BYTES,
    backup_count: int = BACKUP_COUNT,
) -> logging.Logger:
    """
    配置并初始化日志记录器。
    
    参数:
        level: 日志级别，默认为 INFO
        log_to_file: 是否输出到文件，默认为 True
        log_to_console: 是否输出到控制台，默认为 True
        log_dir: 日志文件目录，默认为应用程序 logs 目录
        max_bytes: 单个日志文件最大字节数，默认为 5MB
        backup_count: 保留的备份文件数量，默认为 5
        
    返回:
        配置好的 Logger 实例
    """
    global _logger

    if _logger is not None:
        return _logger

    logger = logging.getLogger("Mysysenv")
    logger.setLevel(level)
    logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    if log_to_file:
        target_dir = log_dir or LOG_DIR
        target_dir.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            target_dir / "mysysenv.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    _logger = logger
    return logger


def get_logger() -> logging.Logger:
    """
    获取日志记录器实例。
    
    如果尚未初始化，则使用默认配置初始化。
    
    返回:
        Logger 实例
    """
    if _logger is None:
        return setup_logger()
    return _logger


def set_log_level(level: int) -> None:
    """
    设置日志级别。
    
    参数:
        level: 日志级别（如 logging.DEBUG、logging.INFO 等）
    """
    logger = get_logger()
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)
