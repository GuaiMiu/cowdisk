"""
@File: monitor.py
@Author: GuaiMiu
@Date: 2026/02/19
@Version: 1.0
@Description: 系统监控接口（路由层）
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from redis import asyncio as aioredis
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.database import get_async_redis, get_async_session
from app.core.exception import AuthException
from app.modules.admin.models.response import ResponseModel
from app.modules.admin.services.auth import AuthService
from app.modules.system.schemas.monitor import ForceLogoutOut, SystemMonitorOut
from app.modules.system.services.monitor import MonitorService
from app.shared.deps import require_permissions, require_user

monitor_router = APIRouter(
    prefix="/monitor",
    tags=["System - Monitor"],
    dependencies=[Depends(require_user)],
)


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
    data = await MonitorService.get_overview(db=db, redis=redis)
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
    data = await MonitorService.force_logout_session(redis=redis, session_id=session_id)
    return ResponseModel.success(data=data, msg="会话已强制下线")

