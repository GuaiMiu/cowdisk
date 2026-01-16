"""
@File: fake_redis.py
@Author: GuaiMiu
@Date: 2025/4/5 20:26
@Version: 1.0
@Description:
"""

import time
from datetime import timedelta


class FakeRedis:
    """用字典模拟的 Redis 客户端，支持 get/set/delete/expire"""

    def __init__(self):
        self.store = {}
        self.expire_times = {}  # key -> 过期时间戳（float）
        self.set_store = {}  # 用于模拟集合类型

    async def get(self, key: str) -> str | None:
        """获取键的值"""
        if self._is_expired(key):
            await self.delete(key)
            return None
        return self.store.get(key)

    async def set(
        self, key: str, value: str, ex: int | float | timedelta = None
    ) -> None:
        """设置键值对，支持过期时间"""
        self.store[key] = value
        if ex:
            expire_in_seconds = (
                ex.total_seconds() if isinstance(ex, timedelta) else float(ex)
            )
            self.expire_times[key] = time.time() + expire_in_seconds
        elif key in self.expire_times:
            self.expire_times.pop(key)

    async def delete(self, key: str):
        """删除键"""
        self.store.pop(key, None)
        self.expire_times.pop(key, None)
        self.set_store.pop(key, None)

    async def expire(self, key: str, seconds: int | float | timedelta) -> bool:
        """设置键的过期时间"""
        if key in self.store:
            expire_in_seconds = (
                seconds.total_seconds()
                if isinstance(seconds, timedelta)
                else float(seconds)
            )
            self.expire_times[key] = time.time() + expire_in_seconds
            return True
        return False

    async def ttl(self, key: str) -> int:
        """返回键的剩余生存时间"""
        if self._is_expired(key):
            await self.delete(key)
            return -1
        if key in self.expire_times:
            remaining = self.expire_times[key] - time.time()
            return max(int(remaining), -1)
        return -1

    async def ping(self) -> bool:
        """模拟 ping 命令"""
        return True

    def _is_expired(self, key: str) -> bool:
        """检查键是否过期"""
        return key in self.expire_times and time.time() > self.expire_times[key]

    async def keys(self) -> list[str]:
        """返回所有键"""
        expired_keys = [key for key in self.store.keys() if self._is_expired(key)]
        for key in expired_keys:
            await self.delete(key)
        return list(self.store.keys())

    async def sadd(self, key: str, *members: str) -> int:
        """将成员添加到集合中，返回实际添加的成员数量"""
        if key not in self.set_store:
            self.set_store[key] = set()  # 如果集合不存在，则初始化

        # 计算新添加的成员数量
        added_count = 0
        for member in members:
            if member not in self.set_store[key]:
                self.set_store[key].add(member)
                added_count += 1
        return added_count

    async def smembers(self, key: str):
        """返回集合中的所有成员"""
        if key in self.set_store:
            return self.set_store[key]
        return None

    async def srem(self, key: str, *members: str) -> int:
        """从集合中移除指定的一个或多个成员，返回实际移除的数量"""
        if key not in self.set_store:
            return 0

        removed_count = 0
        for member in members:
            if member in self.set_store[key]:
                self.set_store[key].remove(member)
                removed_count += 1

        # 如果集合被清空了，可以选择删除这个 key（模拟真实 Redis 行为）
        if not self.set_store[key]:
            del self.set_store[key]

        return removed_count
