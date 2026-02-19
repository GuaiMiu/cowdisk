"""
@File: monitor.py
@Author: GuaiMiu
@Date: 2026/02/19
@Version: 1.0
@Description: 系统监控接口（在线用户、服务健康）
"""

from __future__ import annotations

import ast
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import ctypes
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from redis import asyncio as aioredis
from sqlalchemy import text
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.exception import AuthException
from app.core.database import (
    async_engine,
    async_session,
    get_async_redis,
    get_async_session,
    is_database_configured,
)
from app.enum.redis import RedisInitKeyEnum
from app.modules.admin.models.response import ResponseModel
from app.modules.admin.models.user import User
from app.modules.admin.services.auth import AuthService
from app.modules.system.schemas.monitor import (
    CpuStatusOut,
    DiskStatusOut,
    ForceLogoutOut,
    MemoryStatusOut,
    OnlineSessionOut,
    OnlineUsersOut,
    PythonStatusOut,
    ServerInfoOut,
    ServiceStatusOut,
    ServiceSummaryOut,
    SystemMonitorOut,
)
from app.shared.deps import require_permissions, require_user

monitor_router = APIRouter(
    prefix="/monitor",
    tags=["System - Monitor"],
    dependencies=[Depends(require_user)],
)

APP_START_TS = time.time()


def _normalize_text(value: str | bytes | int | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return str(value)


def _parse_user_id_from_session_key(key: str) -> int | None:
    _, _, user_part = key.rpartition(":")
    if not user_part.isdigit():
        return None
    return int(user_part)


async def _iter_user_session_keys(redis: aioredis.Redis) -> list[str]:
    pattern = f"{RedisInitKeyEnum.USER_SESSIONS.key}:*"
    if hasattr(redis, "scan_iter"):
        keys: list[str] = []
        async for key in redis.scan_iter(match=pattern):
            keys.append(_normalize_text(key))
        return keys
    try:
        raw_keys = await redis.keys(pattern)
    except TypeError:
        raw_keys = await redis.keys()
    return [
        _normalize_text(item)
        for item in raw_keys
        if _normalize_text(item).startswith(f"{RedisInitKeyEnum.USER_SESSIONS.key}:")
    ]


async def _collect_online_sessions(
    db: AsyncSession,
    redis: aioredis.Redis,
) -> OnlineUsersOut:
    session_rows: list[OnlineSessionOut] = []
    user_ids: set[int] = set()
    session_keys = await _iter_user_session_keys(redis)

    for key in session_keys:
        user_id = _parse_user_id_from_session_key(key)
        if user_id is None:
            continue
        members = list(await redis.smembers(key))
        if not members:
            continue
        for member in members:
            session_id = _normalize_text(member)
            if not session_id:
                continue
            token_key = f"{RedisInitKeyEnum.ACCESS_TOKEN.key}:{session_id}"
            access_token = await redis.get(token_key)
            if not access_token:
                await redis.srem(key, session_id)
                continue

            token_ttl_seconds: int | None = None
            if hasattr(redis, "ttl"):
                try:
                    ttl = int(await redis.ttl(token_key))
                    token_ttl_seconds = ttl if ttl >= 0 else None
                except Exception:
                    token_ttl_seconds = None

            login_ip: str | None = None
            user_agent: str | None = None
            device_key = f"{RedisInitKeyEnum.DEVICE_INFO.key}:{session_id}"
            device_info = await redis.get(device_key)
            if device_info:
                parsed = None
                if isinstance(device_info, dict):
                    parsed = device_info
                elif isinstance(device_info, str):
                    try:
                        parsed = ast.literal_eval(device_info)
                    except (SyntaxError, ValueError):
                        parsed = None
                if isinstance(parsed, dict):
                    login_ip = parsed.get("login_ip")
                    user_agent = parsed.get("user_agent")

            session_rows.append(
                OnlineSessionOut(
                    user_id=user_id,
                    session_id=session_id,
                    login_ip=login_ip,
                    user_agent=user_agent,
                    token_ttl_seconds=token_ttl_seconds,
                )
            )
            user_ids.add(user_id)

    if user_ids:
        users = (
            await db.exec(
                select(User.id, User.username).where(
                    User.id.in_(list(user_ids)),
                    User.is_deleted == False,
                )
            )
        ).all()
        username_map = {uid: username for uid, username in users}
    else:
        username_map = {}

    sorted_rows = sorted(session_rows, key=lambda row: (row.user_id, row.session_id))
    for row in sorted_rows:
        row.username = username_map.get(row.user_id)

    return OnlineUsersOut(
        total_users=len({row.user_id for row in sorted_rows}),
        total_sessions=len(sorted_rows),
        sessions=sorted_rows,
    )


async def _find_user_id_by_session(redis: aioredis.Redis, session_id: str) -> int | None:
    device_key = f"{RedisInitKeyEnum.DEVICE_INFO.key}:{session_id}"
    device_info = await redis.get(device_key)
    if isinstance(device_info, str):
        try:
            parsed = ast.literal_eval(device_info)
            if isinstance(parsed, dict):
                value = parsed.get("user_id")
                if isinstance(value, int):
                    return value
                if isinstance(value, str) and value.isdigit():
                    return int(value)
        except (SyntaxError, ValueError):
            pass

    session_keys = await _iter_user_session_keys(redis)
    for key in session_keys:
        members = list(await redis.smembers(key))
        if session_id in {_normalize_text(item) for item in members}:
            return _parse_user_id_from_session_key(key)
    return None


async def _force_logout_session(redis: aioredis.Redis, session_id: str) -> ForceLogoutOut:
    user_id = await _find_user_id_by_session(redis, session_id)

    await redis.delete(f"{RedisInitKeyEnum.ACCESS_TOKEN.key}:{session_id}")
    await redis.delete(f"{RedisInitKeyEnum.REFRESH_TOKEN.key}:{session_id}")
    await redis.delete(f"{RedisInitKeyEnum.DEVICE_INFO.key}:{session_id}")
    await redis.delete(f"{RedisInitKeyEnum.SESSION_META.key}:{session_id}")

    if user_id is not None:
        await redis.srem(f"{RedisInitKeyEnum.USER_SESSIONS.key}:{user_id}", session_id)
    else:
        # 兜底清理，避免 user_id 缺失导致脏会话残留
        session_keys = await _iter_user_session_keys(redis)
        for key in session_keys:
            await redis.srem(key, session_id)

    return ForceLogoutOut(session_id=session_id, user_id=user_id, success=True)


async def _probe_database(db: AsyncSession) -> ServiceStatusOut:
    if not is_database_configured() or not async_engine.is_ready() or not async_session.is_ready():
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


async def _probe_redis(redis: aioredis.Redis) -> ServiceStatusOut:
    if not settings.REDIS_ENABLE:
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


def _probe_storage() -> ServiceStatusOut:
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


def _read_cpu_usage_percent() -> float | None:
    try:
        import psutil  # type: ignore

        return round(float(psutil.cpu_percent(interval=0.1)), 2)
    except Exception:
        pass

    if os.name == "nt":
        try:
            class _FileTime(ctypes.Structure):
                _fields_ = [("dwLowDateTime", ctypes.c_ulong), ("dwHighDateTime", ctypes.c_ulong)]

            def _snapshot():
                idle = _FileTime()
                kernel = _FileTime()
                user = _FileTime()
                ok = ctypes.windll.kernel32.GetSystemTimes(
                    ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
                )
                if not ok:
                    return None
                to_int = lambda ft: (ft.dwHighDateTime << 32) | ft.dwLowDateTime
                return to_int(idle), to_int(kernel), to_int(user)

            s1 = _snapshot()
            if not s1:
                return None
            time.sleep(0.1)
            s2 = _snapshot()
            if not s2:
                return None
            idle = s2[0] - s1[0]
            kernel = s2[1] - s1[1]
            user = s2[2] - s1[2]
            total = kernel + user
            if total <= 0:
                return None
            return round(max(0.0, min(100.0, (total - idle) * 100.0 / total)), 2)
        except Exception:
            return None

    try:
        with open("/proc/stat", "r", encoding="utf-8") as f:
            first = f.readline().split()
        if len(first) < 5 or first[0] != "cpu":
            return None
        values1 = list(map(int, first[1:8]))
        idle1 = values1[3] + values1[4]
        total1 = sum(values1)

        time.sleep(0.1)

        with open("/proc/stat", "r", encoding="utf-8") as f:
            second = f.readline().split()
        values2 = list(map(int, second[1:8]))
        idle2 = values2[3] + values2[4]
        total2 = sum(values2)

        delta_total = total2 - total1
        delta_idle = idle2 - idle1
        if delta_total <= 0:
            return None
        return round(max(0.0, min(100.0, (delta_total - delta_idle) * 100.0 / delta_total)), 2)
    except Exception:
        return None


def _read_memory_status() -> MemoryStatusOut:
    try:
        import psutil  # type: ignore

        vm = psutil.virtual_memory()
        return MemoryStatusOut(
            total_bytes=int(vm.total),
            used_bytes=int(vm.used),
            available_bytes=int(vm.available),
            usage_percent=round(float(vm.percent), 2),
        )
    except Exception:
        pass

    if os.name == "nt":
        try:
            class _MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = _MemoryStatusEx()
            stat.dwLength = ctypes.sizeof(_MemoryStatusEx)
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                return MemoryStatusOut()
            total = int(stat.ullTotalPhys)
            available = int(stat.ullAvailPhys)
            used = max(total - available, 0)
            usage = (used * 100.0 / total) if total > 0 else None
            return MemoryStatusOut(
                total_bytes=total,
                used_bytes=used,
                available_bytes=available,
                usage_percent=round(usage, 2) if usage is not None else None,
            )
        except Exception:
            return MemoryStatusOut()

    try:
        meminfo: dict[str, int] = {}
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                key, raw = line.split(":", 1)
                value = raw.strip().split()[0]
                meminfo[key] = int(value) * 1024
        total = meminfo.get("MemTotal")
        available = meminfo.get("MemAvailable")
        if total is None or available is None:
            return MemoryStatusOut()
        used = max(total - available, 0)
        usage = (used * 100.0 / total) if total > 0 else None
        return MemoryStatusOut(
            total_bytes=total,
            used_bytes=used,
            available_bytes=available,
            usage_percent=round(usage, 2) if usage is not None else None,
        )
    except Exception:
        return MemoryStatusOut()


def _read_disk_status() -> DiskStatusOut:
    root = (settings.DISK_ROOT or "").strip() or "./storage"
    path = Path(root).resolve()
    if not path.exists():
        return DiskStatusOut(path=str(path), status="down")
    try:
        usage = shutil.disk_usage(path)
        total = int(usage.total)
        used = int(usage.used)
        free = int(usage.free)
        percent = (used * 100.0 / total) if total > 0 else None
        return DiskStatusOut(
            path=str(path),
            total_bytes=total,
            used_bytes=used,
            free_bytes=free,
            usage_percent=round(percent, 2) if percent is not None else None,
            status="up",
        )
    except Exception:
        return DiskStatusOut(path=str(path), status="down")


def _read_processor_name() -> str:
    system = platform.system().lower()
    # Windows: platform.processor() 往往是 Family/Model 字符串，优先读取 Win32_Processor.Name。
    if system == "windows":
        commands = [
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)",
            ],
            [
                "wmic",
                "cpu",
                "get",
                "name",
            ],
        ]
        for cmd in commands:
            try:
                completed = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=2,
                    check=False,
                )
                if completed.returncode != 0:
                    continue
                lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
                if not lines:
                    continue
                if len(lines) == 1:
                    return lines[0]
                # wmic 第一行通常是 "Name"，取第一条值。
                return lines[1]
            except Exception:
                continue

    candidates = [
        platform.processor(),
        platform.uname().processor,
        os.environ.get("PROCESSOR_IDENTIFIER"),
        platform.machine(),
    ]
    for item in candidates:
        value = (item or "").strip()
        if value:
            return value
    return ""


def _read_server_info() -> ServerInfoOut:
    return ServerInfoOut(
        hostname=socket.gethostname(),
        os=platform.system(),
        os_release=platform.release(),
        machine=platform.machine(),
        processor=_read_processor_name(),
        app_start_time=datetime.fromtimestamp(APP_START_TS),
    )


def _read_python_status() -> PythonStatusOut:
    uptime = max(time.time() - APP_START_TS, 1.0)
    process_cpu = min(100.0, (time.process_time() / uptime) * 100.0)
    return PythonStatusOut(
        status="running",
        version=platform.python_version(),
        executable=sys.executable,
        implementation=platform.python_implementation(),
        process_id=os.getpid(),
        process_cpu_percent=round(process_cpu, 2),
    )


def _read_cpu_status() -> CpuStatusOut:
    return CpuStatusOut(
        usage_percent=_read_cpu_usage_percent(),
        logical_cores=os.cpu_count(),
    )


def _build_service_summary(services: list[ServiceStatusOut]) -> ServiceSummaryOut:
    summary = ServiceSummaryOut(total=len(services))
    for service in services:
        if service.status == "up":
            summary.up += 1
        elif service.status == "down":
            summary.down += 1
        else:
            summary.degraded += 1
    return summary


@monitor_router.get(
    "/overview",
    summary="系统监控总览",
    response_model=ResponseModel[SystemMonitorOut],
    dependencies=[require_permissions(["cfg:core:read"])],
)
async def get_monitor_overview(
    db: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_async_redis),
):
    online = await _collect_online_sessions(db=db, redis=redis)
    services = [
        await _probe_database(db),
        await _probe_redis(redis),
        _probe_storage(),
    ]
    summary = _build_service_summary(services)
    disk = _read_disk_status()
    data = SystemMonitorOut(
        app_uptime_seconds=max(0, int(time.time() - APP_START_TS)),
        online_users=online,
        cpu=_read_cpu_status(),
        memory=_read_memory_status(),
        disk=disk,
        server=_read_server_info(),
        python=_read_python_status(),
        services=services,
        services_summary=summary,
    )
    return ResponseModel.success(data=data)


@monitor_router.post(
    "/online-users/{session_id}/force-logout",
    summary="强制下线在线会话",
    response_model=ResponseModel[ForceLogoutOut],
    dependencies=[require_permissions(["cfg:core:write"])],
)
async def force_logout_online_user(
    request: Request,
    session_id: str,
    redis: aioredis.Redis = Depends(get_async_redis),
):
    client_ip = request.client.host if request.client else "unknown"
    allowed = await AuthService.apply_rate_limit(
        redis,
        action="force_logout",
        identifier=client_ip,
        limit=settings.AUTH_FORCE_LOGOUT_RATE_LIMIT,
        window_seconds=settings.AUTH_FORCE_LOGOUT_RATE_WINDOW,
    )
    if not allowed:
        raise AuthException(msg="操作过于频繁，请稍后重试")
    data = await _force_logout_session(redis=redis, session_id=session_id)
    return ResponseModel.success(data=data, msg="会话已强制下线")
