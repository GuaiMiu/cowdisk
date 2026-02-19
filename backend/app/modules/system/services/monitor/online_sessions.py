from __future__ import annotations

from dataclasses import dataclass

from redis import asyncio as aioredis
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.enum.redis import RedisInitKeyEnum
from app.modules.admin.models.user import User
from app.modules.system.schemas.monitor import ForceLogoutOut, OnlineSessionOut, OnlineUsersOut
from app.modules.system.services.monitor.utils import (
    normalize_text,
    parse_user_id_from_session_key,
    safe_parse_device_info,
)


@dataclass(frozen=True)
class SessionPair:
    user_id: int
    session_id: str
    user_sessions_key: str


class OnlineSessionProvider:
    async def _iter_user_session_keys(self, redis: aioredis.Redis) -> list[str]:
        pattern = f"{RedisInitKeyEnum.USER_SESSIONS.key}:*"
        if hasattr(redis, "scan_iter"):
            keys: list[str] = []
            async for key in redis.scan_iter(match=pattern, count=500):
                keys.append(normalize_text(key))
            return keys

        raw_keys = await redis.keys(pattern)
        return [normalize_text(key) for key in raw_keys]

    async def _collect_pairs(self, redis: aioredis.Redis) -> list[SessionPair]:
        keys = await self._iter_user_session_keys(redis)
        pairs: list[SessionPair] = []
        for key in keys:
            user_id = parse_user_id_from_session_key(key)
            if user_id is None:
                continue
            members = await redis.smembers(key)
            if not members:
                continue
            for member in members:
                session_id = normalize_text(member).strip()
                if not session_id:
                    continue
                pairs.append(
                    SessionPair(
                        user_id=user_id,
                        session_id=session_id,
                        user_sessions_key=key,
                    )
                )
        return pairs

    async def collect(
        self,
        *,
        db: AsyncSession,
        redis: aioredis.Redis,
        limit: int = 2000,
    ) -> OnlineUsersOut:
        pairs = await self._collect_pairs(redis)
        if not pairs:
            return OnlineUsersOut(total_users=0, total_sessions=0, sessions=[])

        token_keys = [f"{RedisInitKeyEnum.ACCESS_TOKEN.key}:{p.session_id}" for p in pairs]
        device_keys = [f"{RedisInitKeyEnum.DEVICE_INFO.key}:{p.session_id}" for p in pairs]

        pipe = redis.pipeline()
        for key in token_keys:
            pipe.get(key)
        for key in token_keys:
            pipe.ttl(key)
        for key in device_keys:
            pipe.get(key)
        batched = await pipe.execute()

        total = len(pairs)
        token_values = batched[:total]
        ttl_values = batched[total : total * 2]
        device_values = batched[total * 2 : total * 3]

        valid_rows: list[OnlineSessionOut] = []
        all_valid_user_ids: set[int] = set()
        stale_sessions: list[tuple[str, str]] = []

        for idx, pair in enumerate(pairs):
            access_token = token_values[idx]
            if not access_token:
                stale_sessions.append((pair.user_sessions_key, pair.session_id))
                continue

            ttl_seconds: int | None = None
            try:
                ttl = int(ttl_values[idx])
                ttl_seconds = ttl if ttl >= 0 else None
            except Exception:
                ttl_seconds = None

            device_info = safe_parse_device_info(device_values[idx])
            login_ip = device_info.get("login_ip") if isinstance(device_info, dict) else None
            user_agent = device_info.get("user_agent") if isinstance(device_info, dict) else None

            valid_rows.append(
                OnlineSessionOut(
                    user_id=pair.user_id,
                    session_id=pair.session_id,
                    login_ip=login_ip,
                    user_agent=user_agent,
                    token_ttl_seconds=ttl_seconds,
                )
            )
            all_valid_user_ids.add(pair.user_id)

        if stale_sessions:
            stale_pipe = redis.pipeline()
            for user_sessions_key, session_id in stale_sessions:
                stale_pipe.srem(user_sessions_key, session_id)
            await stale_pipe.execute()

        valid_rows.sort(key=lambda row: (row.user_id, row.session_id))
        result_rows = valid_rows[: max(limit, 0)]

        visible_user_ids = {row.user_id for row in result_rows}
        username_map: dict[int, str] = {}
        if visible_user_ids:
            users = (
                await db.exec(
                    select(User.id, User.username).where(
                        User.id.in_(list(visible_user_ids)),
                        User.is_deleted == False,
                    )
                )
            ).all()
            username_map = {uid: username for uid, username in users}

        for row in result_rows:
            row.username = username_map.get(row.user_id)

        return OnlineUsersOut(
            total_users=len(all_valid_user_ids),
            total_sessions=len(valid_rows),
            sessions=result_rows,
        )

    async def _find_user_id_by_session(self, *, redis: aioredis.Redis, session_id: str) -> int | None:
        device_key = f"{RedisInitKeyEnum.DEVICE_INFO.key}:{session_id}"
        device_info = safe_parse_device_info(await redis.get(device_key))
        if isinstance(device_info, dict):
            value = device_info.get("user_id")
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)

        keys = await self._iter_user_session_keys(redis)
        for key in keys:
            user_id = parse_user_id_from_session_key(key)
            if user_id is None:
                continue
            members = await redis.smembers(key)
            member_ids = {normalize_text(item) for item in members}
            if session_id in member_ids:
                return user_id
        return None

    async def force_logout_session(self, *, redis: aioredis.Redis, session_id: str) -> ForceLogoutOut:
        user_id = await self._find_user_id_by_session(redis=redis, session_id=session_id)

        delete_pipe = redis.pipeline()
        delete_pipe.delete(f"{RedisInitKeyEnum.ACCESS_TOKEN.key}:{session_id}")
        delete_pipe.delete(f"{RedisInitKeyEnum.REFRESH_TOKEN.key}:{session_id}")
        delete_pipe.delete(f"{RedisInitKeyEnum.DEVICE_INFO.key}:{session_id}")
        delete_pipe.delete(f"{RedisInitKeyEnum.SESSION_META.key}:{session_id}")
        await delete_pipe.execute()

        if user_id is not None:
            await redis.srem(f"{RedisInitKeyEnum.USER_SESSIONS.key}:{user_id}", session_id)
        else:
            keys = await self._iter_user_session_keys(redis)
            clean_pipe = redis.pipeline()
            for key in keys:
                clean_pipe.srem(key, session_id)
            await clean_pipe.execute()

        return ForceLogoutOut(
            session_id=session_id,
            user_id=user_id,
            success=True,
        )
