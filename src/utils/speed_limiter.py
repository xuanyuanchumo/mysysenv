"""
下载速度限制工具模块。

提供下载速度限制功能。
"""

import time
from typing import BinaryIO

from src.utils.logger import get_logger

logger = get_logger()


class SpeedLimiter:
    """
    下载速度限制器类。
    
    实现简单的下载速度限制功能。
    """
    
    def __init__(self, speed_limit_bytes: int = 0):
        """
        初始化速度限制器。
        
        参数:
            speed_limit_bytes: 速度限制（字节/秒），0 表示不限速
        """
        self.speed_limit = speed_limit_bytes
        self.last_time = time.time()
        self.bytes_read = 0
    
    def write_with_limit(self, f: BinaryIO, data: bytes) -> int:
        """
        写入数据并应用速度限制。
        
        参数:
            f: 文件对象
            data: 要写入的数据
            
        返回:
            实际写入的字节数
        """
        if self.speed_limit <= 0:
            return f.write(data)
        
        chunk_size = len(data)
        written = f.write(data)
        self.bytes_read += written
        
        current_time = time.time()
        elapsed = current_time - self.last_time
        
        if elapsed > 0:
            expected_time = self.bytes_read / self.speed_limit
            if elapsed < expected_time:
                time.sleep(expected_time - elapsed)
        
        self.last_time = time.time()
        self.bytes_read = 0
        
        return written
