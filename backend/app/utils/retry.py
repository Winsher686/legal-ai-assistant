"""通用重试 + 熔断工具。

- retry_call：对可能失败的外部调用做指数退避重试。
- CircuitBreaker：熔断器，连续失败达到阈值后进入 open 状态，
  短时间内直接快速失败，避免雪崩；冷却后进入 half-open 试探。

供 LLM / Embedding 等外部服务调用复用。
"""
import random
import threading
import time
from typing import Callable, Optional, TypeVar

from app.core.config import settings
from app.core.logger import logger

T = TypeVar("T")

# 可重试的异常类型（网络抖动、超时、限流等），不重试编程错误
_RETRYABLE_EXCEPTIONS = (TimeoutError, ConnectionError, OSError)


def retry_call(
    func: Callable[[], T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    backoff: float = 2.0,
    jitter: bool = True,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> T:
    """对 func 做指数退避重试。

    - max_retries：最大重试次数（不含首次调用）。
    - base_delay：首次重试前的等待秒数。
    - backoff：每次重试延迟的倍增系数。
    - jitter：是否加随机抖动，避免惊群。
    仅对 _RETRYABLE_EXCEPTIONS 重试，其余异常直接抛出。
    """
    attempt = 0
    delay = base_delay
    while True:
        try:
            return func()
        except Exception as e:
            if attempt >= max_retries or not isinstance(e, _RETRYABLE_EXCEPTIONS):
                raise
            attempt += 1
            if jitter:
                wait = delay * (1 + random.random() * 0.3)
            else:
                wait = delay
            logger.warning("retry_call attempt %d/%d after error: %s (wait %.2fs)",
                           attempt, max_retries, e, wait)
            if on_retry:
                on_retry(e, attempt)
            time.sleep(wait)
            delay *= backoff


class CircuitBreaker:
    """简单熔断器（线程安全）。

    状态机：closed -> open -> half-open -> closed
    - closed：正常放行，记录连续失败次数，达到 failure_threshold 后 open。
    - open：拒绝所有请求（快速抛 CircuitOpenError），持续 cooldown 秒。
    - half-open：冷却结束后的首次试探，成功则 closed，失败则重新 open。
    """

    class CircuitOpenError(Exception):
        """熔断器打开时的快速失败异常。"""

    def __init__(self, name: str, failure_threshold: int = 5,
                 cooldown: float = 30.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.cooldown = cooldown
        self._failures = 0
        self._opened_at: Optional[float] = None
        self._half_open = False
        self._lock = threading.Lock()

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.time() - self._opened_at >= self.cooldown:
            # 冷却结束，进入 half-open，允许一次试探
            with self._lock:
                self._half_open = True
            return False
        return True

    def __call__(self, func: Callable[[], T]) -> T:
        if self.is_open:
            raise self.CircuitOpenError(
                f"circuit '{self.name}' is open, fast-fail"
            )
        try:
            result = func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        with self._lock:
            self._failures = 0
            self._opened_at = None
            self._half_open = False

    def _on_failure(self):
        with self._lock:
            self._failures += 1
            if self._half_open:
                # half-open 试探失败，立即重新打开
                self._opened_at = time.time()
                self._half_open = False
            elif self._failures >= self.failure_threshold:
                self._opened_at = time.time()
                logger.warning("circuit '%s' opened after %d consecutive failures",
                               self.name, self._failures)


# 全局熔断器实例（供 LLM / Embedding 使用）
_llm_breaker = CircuitBreaker("llm", failure_threshold=5, cooldown=30.0)
_embedding_breaker = CircuitBreaker("embedding", failure_threshold=5, cooldown=30.0)


def get_llm_breaker() -> CircuitBreaker:
    return _llm_breaker


def get_embedding_breaker() -> CircuitBreaker:
    return _embedding_breaker
