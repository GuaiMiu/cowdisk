from __future__ import annotations

import shutil
import time
from pathlib import Path

from redis import asyncio as aioredis
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

import app.core.database as runtime_db
from app.core.config import settings
from app.modules.system.schemas.monitor import ServiceStatusOut, ServiceSummaryOut


class ServiceProbeProvider:
    @staticmethod
    async def probe_database(db: AsyncSession) -> ServiceStatusOut:
        if (
            not runtime_db.is_database_configured()
            or not runtime_db.async_engine.is_ready()
            or not runtime_db.async_session.is_ready()
        ):
            return ServiceStatusOut(name="database", status="degraded", detail="数据库未配置")

        started = time.perf_counter()
        try:
            await db.exec(text("SELECT 1"))
        except Exception as exc:
            return ServiceStatusOut(
                name="database",
                status="down",
                latency_ms=int((time.perf_counter() - started) * 1000),
                detail=f"数据库不可用: {exc}",
            )
        return ServiceStatusOut(
            name="database",
            status="up",
            latency_ms=int((time.perf_counter() - started) * 1000),
            detail="数据库连接正常",
        )

    @staticmethod
    async def probe_redis(redis: aioredis.Redis) -> ServiceStatusOut:
        if bool(getattr(redis, "is_fake", False)):
            return ServiceStatusOut(
                name="redis",
                status="degraded",
                detail="Redis 已禁用，当前使用 FakeRedis",
            )

        started = time.perf_counter()
        try:
            await redis.ping()
        except Exception as exc:
            return ServiceStatusOut(
                name="redis",
                status="down",
                latency_ms=int((time.perf_counter() - started) * 1000),
                detail=f"Redis 不可用: {exc}",
            )
        return ServiceStatusOut(
            name="redis",
            status="up",
            latency_ms=int((time.perf_counter() - started) * 1000),
            detail="Redis 连接正常",
        )

    @staticmethod
    def probe_storage() -> ServiceStatusOut:
        root = (settings.DISK_ROOT or "").strip() or "./storage"
        path = Path(root).resolve()
        if not path.exists():
            return ServiceStatusOut(
                name="storage",
                status="down",
                detail=f"存储路径不存在: {path}",
            )
        try:
            usage = shutil.disk_usage(path)
        except Exception as exc:
            return ServiceStatusOut(
                name="storage",
                status="down",
                detail=f"存储不可用: {exc}",
            )

        free_gb = usage.free / 1024 / 1024 / 1024
        return ServiceStatusOut(
            name="storage",
            status="up",
            detail=f"路径: {path}，剩余空间: {free_gb:.2f} GB",
        )

    @staticmethod
    def summarize(services: list[ServiceStatusOut]) -> ServiceSummaryOut:
        summary = ServiceSummaryOut(total=len(services))
        for service in services:
            if service.status == "up":
                summary.up += 1
            elif service.status == "down":
                summary.down += 1
            else:
                summary.degraded += 1
        return summary
