"""
core/limiter.py — 三级异步信号量限流
层级：全局 → API Key → 厂商
"""
from __future__ import annotations
import asyncio
import logging
from collections import defaultdict
from core.config import settings

logger = logging.getLogger("gateway.limiter")

# ── 全局并发信号量 ───────────────────────────────────────────
_global_semaphore = asyncio.Semaphore(settings.global_max_concurrency)

# ── 按 API Key 维度的信号量字典 ─────────────────────────────
# key: key_id(str) -> asyncio.Semaphore
_key_semaphores: dict[str, asyncio.Semaphore] = defaultdict()
_key_sem_lock = asyncio.Lock()

# ── 按厂商维度的信号量字典 ──────────────────────────────────
# key: provider_name(str) -> asyncio.Semaphore
_provider_semaphores: dict[str, asyncio.Semaphore] = {}
_provider_sem_lock = asyncio.Lock()


async def get_key_semaphore(key_id: str, max_concurrency: int) -> asyncio.Semaphore:
    """懒创建：按 key_id 返回对应信号量"""
    if key_id not in _key_semaphores:
        async with _key_sem_lock:
            if key_id not in _key_semaphores:
                _key_semaphores[key_id] = asyncio.Semaphore(max_concurrency)
    return _key_semaphores[key_id]


async def get_provider_semaphore(provider_name: str, max_concurrency: int) -> asyncio.Semaphore:
    """懒创建：按厂商名返回对应信号量"""
    if provider_name not in _provider_semaphores:
        async with _provider_sem_lock:
            if provider_name not in _provider_semaphores:
                _provider_semaphores[provider_name] = asyncio.Semaphore(max_concurrency)
    return _provider_semaphores[provider_name]


class RateLimitExceeded(Exception):
    """限流异常"""
    def __init__(self, level: str):
        super().__init__(f"Rate limit exceeded at level: {level}")
        self.level = level


class ConcurrencyGuard:
    """
    三级并发守卫，使用 async context manager。
    使用方式：
        async with ConcurrencyGuard(key_id, key_max, provider_name, provider_max):
            ...
    """
    def __init__(
        self,
        key_id: str,
        key_max_concurrency: int,
        provider_name: str,
        provider_max_concurrency: int,
    ):
        self.key_id = key_id
        self.key_max = key_max_concurrency
        self.provider_name = provider_name
        self.provider_max = provider_max_concurrency
        self._acquired: list[asyncio.Semaphore] = []

    async def __aenter__(self):
        # 1. 全局限流
        if not _global_semaphore._value:  # 快速预检，避免等待
            logger.warning("[限流] 全局并发已满，拒绝请求 key=%s", self.key_id)
            raise RateLimitExceeded("global")
        await _global_semaphore.acquire()
        self._acquired.append(_global_semaphore)

        # 2. API Key 限流
        key_sem = await get_key_semaphore(self.key_id, self.key_max)
        if not key_sem._value:
            logger.warning("[限流] Key 并发已满，拒绝请求 key=%s", self.key_id)
            _global_semaphore.release()
            self._acquired.remove(_global_semaphore)
            raise RateLimitExceeded("api_key")
        await key_sem.acquire()
        self._acquired.append(key_sem)

        # 3. 厂商限流
        provider_sem = await get_provider_semaphore(self.provider_name, self.provider_max)
        if not provider_sem._value:
            logger.warning("[限流] 厂商并发已满，拒绝请求 provider=%s key=%s",
                           self.provider_name, self.key_id)
            for sem in reversed(self._acquired):
                sem.release()
            self._acquired.clear()
            raise RateLimitExceeded("provider")
        await provider_sem.acquire()
        self._acquired.append(provider_sem)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # 逆序释放所有已获取的信号量
        for sem in reversed(self._acquired):
            sem.release()
        self._acquired.clear()
        return False
