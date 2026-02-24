"""
速率限制器模块。

提供请求频率控制功能，支持最小时间间隔和 Token Bucket 两种策略。
"""

import time
import threading
from typing import Optional


class RateLimiter:
    """
    速率限制器类，用于控制请求频率。

    支持两种策略：
    1. 最小时间间隔策略：确保两次请求之间的间隔不少于指定时间
    2. Token Bucket 策略：按固定速率生成 token，请求消耗 token
    """

    def __init__(
        self,
        min_interval: float = 0.0,
        requests_per_second: Optional[float] = None,
        max_tokens: Optional[float] = None,
    ) -> None:
        """
        初始化速率限制器。

        参数:
            min_interval: 最小请求间隔（秒），默认为 0
            requests_per_second: 每秒允许的请求数，用于 Token Bucket 策略
            max_tokens: Token Bucket 的最大容量，默认为 requests_per_second
        """
        self.min_interval = min_interval
        self.last_request_time = 0.0
        self._lock = threading.Lock()

        self.requests_per_second = requests_per_second
        if requests_per_second is not None:
            self.tokens = float(max_tokens or requests_per_second)
            self.max_tokens = float(max_tokens or requests_per_second)
            self.last_token_refill_time = time.time()
        else:
            self.tokens = None
            self.max_tokens = None
            self.last_token_refill_time = None

    def acquire(self) -> None:
        """
        获取请求权限，必要时等待。

        此方法会阻塞直到可以发送请求。
        """
        with self._lock:
            now = time.time()

            if self.requests_per_second is not None:
                self._refill_tokens(now)

                while self.tokens < 1.0:
                    wait_time = (1.0 - self.tokens) / self.requests_per_second
                    time.sleep(wait_time)
                    now = time.time()
                    self._refill_tokens(now)

                self.tokens -= 1.0
                self.last_request_time = now

            else:
                time_since_last = now - self.last_request_time
                if time_since_last < self.min_interval:
                    wait_time = self.min_interval - time_since_last
                    time.sleep(wait_time)
                    self.last_request_time = time.time()
                else:
                    self.last_request_time = now

    def _refill_tokens(self, now: float) -> None:
        """
        补充 Token Bucket 中的 token。

        参数:
            now: 当前时间戳
        """
        if self.last_token_refill_time is None:
            return

        time_passed = now - self.last_token_refill_time
        new_tokens = time_passed * self.requests_per_second
        self.tokens = min(self.max_tokens, self.tokens + new_tokens)
        self.last_token_refill_time = now

    def reset(self) -> None:
        """
        重置速率限制器状态。
        """
        with self._lock:
            self.last_request_time = 0.0
            if self.requests_per_second is not None:
                self.tokens = self.max_tokens
                self.last_token_refill_time = time.time()
