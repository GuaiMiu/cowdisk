"""
@File: usecase.py
@Author: GuaiMiu
@Date: 2026/02/10
@Version: 1.0
@Description: 审计日志用例
"""

from __future__ import annotations

from datetime import datetime

from sqlmodel.ext.asyncio.session import AsyncSession

from app.audit.decorator import audited
from app.audit.repo import AuditRepo


def _audit_action_detail(action: str):
    def _extractor(*_args, **_kwargs):
        return {"detail": {"action": action}}

    return _extractor


class AuditUsecase:
    @staticmethod
    async def list_logs(
        db: AsyncSession,
        *,
        start: datetime | None,
        end: datetime | None,
        user_id: int | None,
        action: str | None,
        status: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
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

    @staticmethod
    @audited(
        "AUDIT_EXPORT",
        resource_type="AUDIT",
        extractors=[_audit_action_detail("AUDIT_EXPORT")],
        auto_commit=True,
    )
    async def export_logs(
        db: AsyncSession,
        *,
        start: datetime | None,
        end: datetime | None,
        user_id: int | None,
        action: str | None,
        status: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
        commit: bool = False,
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

    @staticmethod
    @audited(
        "AUDIT_CLEANUP",
        resource_type="AUDIT",
        extractors=[_audit_action_detail("AUDIT_CLEANUP")],
        auto_commit=True,
    )
    async def cleanup_logs(
        db: AsyncSession,
        retention_days: int,
        commit: bool = True,
    ) -> int:
        return await AuditRepo.cleanup(db, retention_days, commit=commit)
