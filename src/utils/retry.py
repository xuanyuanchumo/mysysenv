"""
重试机制工具模块。

提供指数退避重试策略，用于处理临时性网络错误。
"""

import time
import random
from typing import Callable, TypeVar, Tuple, Optional, Any
from functools import wraps

from src.utils.logger import get_logger

logger = get_logger()

T = TypeVar('T')


class RetryHandler:
    """
    重试处理器类。
    
    实现指数退避重试策略，用于处理临时性错误。
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True
    ):
        """
        初始化重试处理器。
        
        参数:
            max_retries: 最大重试次数
            base_delay: 基础延迟时间（秒）
            max_delay: 最大延迟时间（秒）
            backoff_factor: 退避因子
            jitter: 是否添加随机抖动
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        计算第 n 次重试的延迟时间。
        
        参数:
            attempt: 重试次数（从 0 开始）
            
        返回:
            延迟时间（秒）
        """
        delay = self.base_delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay
    
    def _is_retryable_error(self, exception: Exception) -> bool:
        """
        判断错误是否可重试。
        
        参数:
            exception: 异常对象
            
        返回:
            可重试返回 True，否则返回 False
        """
        import requests
        
        retryable_exceptions = (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError,
            requests.exceptions.ChunkedEncodingError,
        )
        
        if isinstance(exception, retryable_exceptions):
            if isinstance(exception, requests.exceptions.HTTPError):
                if hasattr(exception, 'response') and exception.response is not None:
                    status_code = exception.response.status_code
                    if status_code >= 500 or status_code in [408, 429]:
                        return True
                    return False
            return True
        
        return False
    
    def execute(
        self,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any
    ) -> T:
        """
        执行函数，失败时自动重试。
        
        参数:
            func: 要执行的函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数
            
        返回:
            函数执行结果
            
        抛出:
            超过最大重试次数后抛出最后一次异常
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if not self._is_retryable_error(e):
                    logger.warning(f"遇到不可重试的错误: {e}")
                    raise
                
                if attempt >= self.max_retries:
                    logger.error(f"已达到最大重试次数 {self.max_retries}，放弃重试")
                    raise
                
                delay = self._calculate_delay(attempt)
                logger.warning(
                    f"请求失败 (尝试 {attempt + 1}/{self.max_retries + 1}): {e}，"
                    f"{delay:.2f} 秒后重试..."
                )
                time.sleep(delay)
        
        raise last_exception


def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True
):
    """
    重试装饰器。
    
    参数:
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        backoff_factor: 退避因子
        jitter: 是否添加随机抖动
        
    返回:
        装饰器函数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            handler = RetryHandler(
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                backoff_factor=backoff_factor,
                jitter=jitter
            )
            return handler.execute(func, *args, **kwargs)
        return wrapper
    return decorator
