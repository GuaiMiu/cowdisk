from __future__ import annotations

import time
from dataclasses import dataclass

from redis import asyncio as aioredis
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.system.schemas.monitor import ForceLogoutOut, SystemMonitorOut
from app.modules.system.services.monitor.metrics import SystemMetricsProvider
from app.modules.system.services.monitor.online_sessions import OnlineSessionProvider
from app.modules.system.services.monitor.platform_info import ServerInfoProvider
from app.modules.system.services.monitor.probes import ServiceProbeProvider
from app.modules.system.services.monitor.python_info import PythonInfoProvider


@dataclass
class _OverviewCache:
    ts: float = 0.0
    data: SystemMonitorOut | None = None


class MonitorFacade:
    def __init__(self, *, app_start_ts: float | None = None) -> None:
        self._online_provider = OnlineSessionProvider()
        self._probe_provider = ServiceProbeProvider()
        self._metrics_provider = SystemMetricsProvider()
        self._server_provider = ServerInfoProvider(app_start_ts=app_start_ts)
        self._python_provider = PythonInfoProvider()
        self._cache = _OverviewCache()

    async def get_overview(
        self,
        *,
        db: AsyncSession,
        redis: aioredis.Redis,
        session_limit: int = 2000,
        cache_seconds: float = 1.0,
    ) -> SystemMonitorOut:
        now = time.time()
        if self._cache.data is not None and (now - self._cache.ts) <= cache_seconds:
            return self._cache.data.model_copy(deep=True)

        online = await self._online_provider.collect(db=db, redis=redis, limit=session_limit)
        services = [
            await self._probe_provider.probe_database(db),
            await self._probe_provider.probe_redis(redis),
            self._probe_provider.probe_storage(),
        ]
        summary = self._probe_provider.summarize(services)

        data = SystemMonitorOut(
            app_uptime_seconds=max(0, int(now - self._server_provider.app_start_ts)),
            online_users=online,
            cpu=self._metrics_provider.read_cpu_status(),
            memory=self._metrics_provider.read_memory_status(),
            disk=self._metrics_provider.read_disk_status(),
            server=self._server_provider.read(),
            python=self._python_provider.read(),
            services=services,
            services_summary=summary,
        )
        self._cache = _OverviewCache(ts=now, data=data)
        return data.model_copy(deep=True)

    async def force_logout_session(self, *, redis: aioredis.Redis, session_id: str) -> ForceLogoutOut:
        return await self._online_provider.force_logout_session(redis=redis, session_id=session_id)
