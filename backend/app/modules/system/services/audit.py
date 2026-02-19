"""
@File: audit.py
@Author: GuaiMiu
@Date: 2026/02/10
@Version: 2.0
@Description: 审计日志服务
"""

from __future__ import annotations

from datetime import datetime

from sqlmodel.ext.asyncio.session import AsyncSession

from app.audit.repo import AuditRepo


class AuditService:
    @classmethod
    async def cleanup(cls, retention_days: int, db: AsyncSession) -> int:
        return await AuditRepo.cleanup(db, retention_days)

    @classmethod
    async def list_logs(
        cls,
        *,
        start: datetime | None,
        end: datetime | None,
        user_id: int | None,
        action: str | None,
        status: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
        db: AsyncSession,
    ):
        return await AuditRepo.list_logs(
            db,
            start=start,
            end=end,
            user_id=user_id,
            action=action,
            status=status,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )

