"""API 限流工具（固定窗口计数 + Redis，Mock/无 Redis 时内存兜底）。

- RateLimiter：按 key 做固定窗口限流，返回是否放行。
- 生产环境用 Redis（原子 INCR + EXPIRE），支持多 worker 共享计数；
  Mock/本地环境用线程安全的内存字典。
"""
import threading
import time
from typing import Dict, Optional

from app.core.config import settings
from app.core.logger import logger

_redis = None


def _get_redis():
    global _redis
    if _redis is not None:
        return _redis
    if settings.USE_MOCK:
        return None
    try:
        import redis

        _redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        _redis.ping()
    except Exception as e:
        logger.warning("redis connect failed(%s), fallback to in-memory rate limit", e)
        _redis = None
    return _redis


class RateLimiter:
    """固定窗口限流器。"""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # 内存兜底：key -> (window_start, count)
        self._mem: Dict[str, tuple] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """判断该 key 是否允许本次请求。"""
        r = _get_redis()
        if r is not None:
            return self._allow_redis(r, key)
        return self._allow_memory(key)

    def _allow_redis(self, r, key: str) -> bool:
        try:
            pipe = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, self.window_seconds)
            count = pipe.execute()[0]
            return int(count) <= self.max_requests
        except Exception as e:
            logger.warning("redis rate limit failed(%s), fallback memory", e)
            return self._allow_memory(key)

    def _allow_memory(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            window_start, count = self._mem.get(key, (now, 0))
            if now - window_start >= self.window_seconds:
                window_start, count = now, 0
            if count >= self.max_requests:
                return False
            self._mem[key] = (window_start, count + 1)
            return True


# 全局限流器：默认每用户每分钟 60 次（可调）
_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter(
            max_requests=settings.RATE_LIMIT_MAX_REQUESTS,
            window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
        )
    return _limiter
