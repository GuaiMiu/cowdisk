from __future__ import annotations

import time

from redis import asyncio as aioredis
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.errors.codes import CommonCode
from app.core.errors.exceptions import AppException
from app.modules.admin.services.auth import AuthService
from app.modules.system.schemas.monitor import ForceLogoutOut, SystemMonitorOut
from app.modules.system.services.monitor.facade import MonitorFacade

_APP_START_TS = time.time()
_MONITOR_FACADE = MonitorFacade(app_start_ts=_APP_START_TS)


class MonitorService:
    @staticmethod
    async def get_overview(db: AsyncSession, redis: aioredis.Redis) -> SystemMonitorOut:
        return await _MONITOR_FACADE.get_overview(db=db, redis=redis)

    @staticmethod
    async def force_logout_session(redis: aioredis.Redis, session_id: str) -> ForceLogoutOut:
        return await _MONITOR_FACADE.force_logout_session(redis=redis, session_id=session_id)

    @staticmethod
    async def force_logout_online_user(
        *,
        redis: aioredis.Redis,
        session_id: str,
        client_ip: str,
    ) -> ForceLogoutOut:
        allowed = await AuthService.apply_rate_limit(
            redis,
            action="force_logout",
            identifier=client_ip or "unknown",
            limit=settings.AUTH_FORCE_LOGOUT_RATE_LIMIT,
            window_seconds=settings.AUTH_FORCE_LOGOUT_RATE_WINDOW,
        )
        if not allowed:
            raise AppException(http_status=429, code=int(CommonCode.RATE_LIMITED), message="操作过于频繁，请稍后重试")
        return await _MONITOR_FACADE.force_logout_session(redis=redis, session_id=session_id)


__all__ = ["MonitorFacade", "MonitorService"]
