from __future__ import annotations

import time

from redis import asyncio as aioredis
from sqlmodel.ext.asyncio.session import AsyncSession

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


__all__ = ["MonitorFacade", "MonitorService"]
