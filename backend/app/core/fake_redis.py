"""
@File: fake_redis.py
@Author: GuaiMiu
@Date: 2025/4/5 20:26
@Version: 2.0
@Description:
    FakeRedis: 用内存结构模拟一小部分 redis-py asyncio 客户端行为。
    目标：
    - 常用 API 签名尽量兼容（get/set/setex/delete/expire/ttl/keys/exists/incr/mget/mset）
    - 支持 string / set / hash
    - TTL 语义尽量贴近 Redis:
        * key 不存在: ttl = -2
        * key 存在但无过期: ttl = -1
        * key 存在且有过期: ttl >= 0
    - 不做后台线程清理；访问时惰性清理
"""

from __future__ import annotations

import fnmatch
import time
from datetime import timedelta
from typing import Any, Iterable


SecondsLike = int | float | timedelta


class FakeRedis:
    """
    用字典模拟的 Redis 客户端（async 风格），支持：
    - String: get/set/setex/mget/mset/exists/delete/incr
    - TTL: expire/ttl
    - Keys: keys(pattern)
    - Set: sadd/smembers/srem
    - Hash: hset/hget/hgetall/hdel/hexists
    - ping
    """

    def __init__(self):
        # string
        self.store: dict[str, str] = {}

        # key -> expire timestamp (float)
        self.expire_times: dict[str, float] = {}

        # set
        self.set_store: dict[str, set[str]] = {}

        # hash
        self.hash_store: dict[str, dict[str, str]] = {}

    # -----------------------
    # helpers
    # -----------------------

    def _now(self) -> float:
        return time.time()

    def _seconds(self, ex: SecondsLike) -> float:
        return ex.total_seconds() if isinstance(ex, timedelta) else float(ex)

    def _key_exists(self, key: str) -> bool:
        return key in self.store or key in self.set_store or key in self.hash_store

    def _is_expired(self, key: str) -> bool:
        ts = self.expire_times.get(key)
        return ts is not None and self._now() > ts

    async def _purge_if_expired(self, key: str) -> bool:
        """
        如果 key 已过期：删除并返回 True，否则 False
        """
        if self._is_expired(key):
            await self.delete(key)
            return True
        return False

    # -----------------------
    # basic / health
    # -----------------------

    async def ping(self) -> bool:
        return True

    # -----------------------
    # string
    # -----------------------

    async def get(self, key: str) -> str | None:
        if await self._purge_if_expired(key):
            return None
        return self.store.get(key)

    async def set(
        self,
        key: str,
        value: str,
        ex: SecondsLike | None = None,
        px: SecondsLike | None = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """
        兼容一部分 redis-py:
        - ex: 秒
        - px: 毫秒（这里也当 seconds-like 处理，若传 int 毫秒你可自己换算；为了简单不做自动 ms->s）
        - nx: 仅当不存在时设置
        - xx: 仅当存在时设置
        返回：
        - True: 设置成功
        - False: 未设置（nx/xx 条件不满足）
        """
        # 先清理过期
        await self._purge_if_expired(key)

        exists = self._key_exists(key)

        if nx and exists:
            return False
        if xx and not exists:
            return False

        self.store[key] = str(value)

        # ttl
        ttl = None
        if ex is not None:
            ttl = self._seconds(ex)
        elif px is not None:
            ttl = self._seconds(px)

        if ttl is not None and ttl > 0:
            self.expire_times[key] = self._now() + ttl
        else:
            # 不设置/清除 ttl
            self.expire_times.pop(key, None)

        return True

    async def setex(self, key: str, time_seconds: SecondsLike, value: str) -> bool:
        return await self.set(key, value, ex=time_seconds)

    async def mget(self, keys: Iterable[str]) -> list[str | None]:
        res: list[str | None] = []
        for k in keys:
            res.append(await self.get(k))
        return res

    async def mset(self, mapping: dict[str, Any]) -> bool:
        for k, v in mapping.items():
            await self.set(str(k), str(v))
        return True

    async def exists(self, *keys: str) -> int:
        """
        返回存在的 key 数量（redis 行为）
        """
        count = 0
        for k in keys:
            if await self._purge_if_expired(k):
                continue
            if self._key_exists(k):
                count += 1
        return count

    async def incr(self, key: str, amount: int = 1) -> int:
        """
        简化版 INCRBY：只支持 int
        """
        if await self._purge_if_expired(key):
            # 过期后当不存在
            current = 0
        else:
            raw = self.store.get(key)
            current = int(raw) if raw is not None else 0

        current += int(amount)
        # INCR 会写回 string value，并保持原 ttl（Redis 会保持 ttl）
        # 这里我们也保持：如果原来有 expire_times[key] 就不动
        self.store[key] = str(current)
        return current

    # -----------------------
    # ttl / expire
    # -----------------------

    async def expire(self, key: str, seconds: SecondsLike) -> bool:
        """
        key 存在且未过期 -> 设置 ttl 返回 True
        key 不存在/已过期 -> False
        """
        if await self._purge_if_expired(key):
            return False
        if not self._key_exists(key):
            return False
        ttl = self._seconds(seconds)
        if ttl <= 0:
            # Redis: expire <=0 等价于立即过期；这里做 delete
            await self.delete(key)
            return True
        self.expire_times[key] = self._now() + ttl
        return True

    async def ttl(self, key: str) -> int:
        """
        Redis 语义：
        -2: key 不存在
        -1: key 存在但无过期
        >=0: 剩余秒数
        """
        if await self._purge_if_expired(key):
            return -2
        if not self._key_exists(key):
            return -2
        if key not in self.expire_times:
            return -1
        remaining = self.expire_times[key] - self._now()
        # 若出现极小负值，按 -2（已过期）处理
        if remaining <= 0:
            await self.delete(key)
            return -2
        return int(remaining)

    # -----------------------
    # delete / keys
    # -----------------------

    async def delete(self, *keys: str) -> int:
        """
        兼容 redis: delete(*keys) -> 删除数量
        """
        removed = 0
        for key in keys:
            existed = self._key_exists(key)
            self.store.pop(key, None)
            self.expire_times.pop(key, None)
            self.set_store.pop(key, None)
            self.hash_store.pop(key, None)
            if existed:
                removed += 1
        return removed

    async def keys(self, pattern: str = "*") -> list[str]:
        """
        兼容 redis: keys(pattern="*")
        使用 fnmatch 做简单通配符匹配（*, ?, []）
        """
        # 惰性清理：遍历所有 key，把过期的删了
        all_keys = set(self.store.keys()) | set(self.set_store.keys()) | set(self.hash_store.keys())
        expired = [k for k in all_keys if self._is_expired(k)]
        if expired:
            await self.delete(*expired)

        all_keys = set(self.store.keys()) | set(self.set_store.keys()) | set(self.hash_store.keys())
        if pattern in ("*", ""):
            return list(all_keys)

        return [k for k in all_keys if fnmatch.fnmatch(k, pattern)]

    # -----------------------
    # set
    # -----------------------

    async def sadd(self, key: str, *members: str) -> int:
        """
        返回实际添加的成员数量
        """
        await self._purge_if_expired(key)

        if key not in self.set_store:
            self.set_store[key] = set()

        added = 0
        for m in members:
            m = str(m)
            if m not in self.set_store[key]:
                self.set_store[key].add(m)
                added += 1
        return added

    async def smembers(self, key: str) -> set[str]:
        await self._purge_if_expired(key)
        return set(self.set_store.get(key, set()))

    async def srem(self, key: str, *members: str) -> int:
        await self._purge_if_expired(key)
        if key not in self.set_store:
            return 0

        removed = 0
        for m in members:
            m = str(m)
            if m in self.set_store[key]:
                self.set_store[key].remove(m)
                removed += 1

        if not self.set_store[key]:
            del self.set_store[key]
        return removed

    # -----------------------
    # hash
    # -----------------------

    async def hset(self, key: str, mapping: dict | None = None, **kwargs) -> int:
        """
        支持：
        - hset(key, mapping={...})
        - hset(key, field=value, ...)
        返回新增字段数量（贴近 redis）
        """
        await self._purge_if_expired(key)

        if mapping is None:
            mapping = {}
        if kwargs:
            mapping = {**mapping, **kwargs}

        if key not in self.hash_store:
            self.hash_store[key] = {}

        added = 0
        for field, value in mapping.items():
            f = str(field)
            v = str(value)
            if f not in self.hash_store[key]:
                added += 1
            self.hash_store[key][f] = v
        return added

    async def hget(self, key: str, field: str) -> str | None:
        if await self._purge_if_expired(key):
            return None
        h = self.hash_store.get(key)
        if not h:
            return None
        return h.get(str(field))

    async def hgetall(self, key: str) -> dict[str, str]:
        if await self._purge_if_expired(key):
            return {}
        return dict(self.hash_store.get(key, {}))

    async def hdel(self, key: str, *fields: str) -> int:
        await self._purge_if_expired(key)
        h = self.hash_store.get(key)
        if not h:
            return 0
        removed = 0
        for f in fields:
            f = str(f)
            if f in h:
                del h[f]
                removed += 1
        if not h:
            self.hash_store.pop(key, None)
        return removed

    async def hexists(self, key: str, field: str) -> bool:
        if await self._purge_if_expired(key):
            return False
        h = self.hash_store.get(key)
        if not h:
            return False
        return str(field) in h
