"""
下载历史记录模块。

记录下载历史和状态。
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.utils.logger import get_logger

logger = get_logger()


class DownloadHistory:
    """
    下载历史记录类。
    
    记录下载任务的历史和状态。
    """
    
    def __init__(self, config_dir: Path):
        """
        初始化下载历史记录器。
        
        参数:
            config_dir: 配置目录路径
        """
        self.history_file = config_dir / "download_history.json"
        self.history: List[Dict[str, Any]] = []
        self._load_history()
    
    def _load_history(self) -> None:
        """加载历史记录文件。"""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except Exception as e:
                logger.warning(f"加载下载历史失败: {e}")
                self.history = []
    
    def _save_history(self) -> None:
        """保存历史记录到文件。"""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"保存下载历史失败: {e}")
    
    def add_record(
        self,
        tool: str,
        version: str,
        status: str,
        error_message: Optional[str] = None,
        download_url: Optional[str] = None
    ) -> None:
        """
        添加一条下载记录。
        
        参数:
            tool: 工具名称
            version: 版本号
            status: 状态（success/failed）
            error_message: 错误信息（可选）
            download_url: 下载 URL（可选）
        """
        record = {
            "tool": tool,
            "version": version,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "error_message": error_message,
            "download_url": download_url
        }
        
        self.history.insert(0, record)
        
        if len(self.history) > 100:
            self.history = self.history[:100]
        
        self._save_history()
        logger.info(f"记录下载历史: {tool} {version} - {status}")
    
    def get_history(self, tool: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取下载历史记录。
        
        参数:
            tool: 工具名称（可选，过滤用）
            limit: 返回记录的最大数量
            
        返回:
            下载历史记录列表
        """
        if tool:
            filtered = [r for r in self.history if r.get("tool") == tool]
            return filtered[:limit]
        return self.history[:limit]
    
    def clear_history(self) -> None:
        """清空历史记录。"""
        self.history = []
        self._save_history()
        logger.info("清空下载历史")
