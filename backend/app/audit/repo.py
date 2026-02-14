"""
@File: repo.py
@Author: GuaiMiu
@Date: 2026/02/10
@Version: 1.0
@Description: 审计查询与 outbox 处理仓储
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, update
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.audit.constants import AuditOutboxStatus
from app.audit.models import AuditLog, AuditOutbox


class AuditRepo:
    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now()

    @staticmethod
    def _parse_event_time(value: str | None) -> datetime:
        if not value:
            return AuditRepo._utc_now()
        normalized = value.replace("Z", "")
        return datetime.fromisoformat(normalized)

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
    ) -> tuple[int, list[AuditLog]]:
        stmt = select(AuditLog)
        if start:
            stmt = stmt.where(AuditLog.created_at >= start)
        if end:
            stmt = stmt.where(AuditLog.created_at <= end)
        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if status:
            stmt = stmt.where(AuditLog.status == status)
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(
                AuditLog.resource_id.like(like)
                | AuditLog.path.like(like)
                | AuditLog.detail.like(like)
            )
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.exec(count_stmt)).one()
        items = (
            await db.exec(
                stmt.order_by(AuditLog.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return int(total or 0), items

    @staticmethod
    async def cleanup(
        db: AsyncSession, retention_days: int, commit: bool = True
    ) -> int:
        threshold = AuditRepo._utc_now() - timedelta(days=retention_days)
        result = await db.exec(
            AuditLog.__table__.delete().where(AuditLog.created_at < threshold)
        )
        if commit:
            await db.commit()
        return int(result.rowcount or 0)

    @staticmethod
    async def upsert_log(db: AsyncSession, payload: dict[str, Any]) -> None:
        table = AuditLog.__table__
        dialect = db.get_bind().dialect.name
        values = {
            "event_id": payload.get("event_id"),
            "user_id": payload.get("user_id"),
            "action": payload.get("action"),
            "status": payload.get("status"),
            "resource_type": payload.get("resource_type"),
            "resource_id": payload.get("resource_id"),
            "path": payload.get("path"),
            "ip": payload.get("ip"),
            "user_agent": payload.get("user_agent"),
            "request_id": payload.get("request_id"),
            "trace_id": payload.get("trace_id"),
            "duration_ms": payload.get("duration_ms"),
            "detail": json.dumps(payload.get("detail"), ensure_ascii=False)
            if payload.get("detail") is not None
            else None,
            "created_at": AuditRepo._parse_event_time(payload.get("created_at")),
        }
        if dialect == "mysql":
            stmt = mysql_insert(table).values(**values)
            stmt = stmt.on_duplicate_key_update(event_id=stmt.inserted.event_id)
            await db.exec(stmt)
            return
        if dialect == "sqlite":
            stmt = sqlite_insert(table).values(**values)
            stmt = stmt.on_conflict_do_nothing(index_elements=["event_id"])
            await db.exec(stmt)
            return
        stmt = table.insert().values(**values)
        await db.exec(stmt)

    @staticmethod
    async def claim_outbox(
        db: AsyncSession,
        *,
        batch_size: int,
        worker_id: str,
        lock_timeout_seconds: int,
        retry_delay_seconds: int,
        use_skip_locked: bool,
    ) -> list[AuditOutbox]:
        now = AuditRepo._utc_now()
        cutoff = now - timedelta(seconds=lock_timeout_seconds)
        retry_cutoff = now - timedelta(seconds=max(1, retry_delay_seconds))
        retryable_pending = (
            (AuditOutbox.status == AuditOutboxStatus.PENDING)
            & (
                (AuditOutbox.attempts <= 0)
                | (AuditOutbox.updated_at.is_(None))
                | (AuditOutbox.updated_at < retry_cutoff)
            )
        )
        reclaimable = or_(
            retryable_pending,
            (
                (AuditOutbox.status == AuditOutboxStatus.PROCESSING)
                & AuditOutbox.locked_at.is_not(None)
                & (AuditOutbox.locked_at < cutoff)
            ),
        )
        if use_skip_locked:
            stmt = (
                select(AuditOutbox)
                .where(reclaimable)
                .order_by(AuditOutbox.created_at.asc())
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            )
            rows = (await db.exec(stmt)).all()
            if not rows:
                return []
            for row in rows:
                row.status = AuditOutboxStatus.PROCESSING
                row.locked_at = now
                row.locked_by = worker_id
                row.updated_at = now
            await db.commit()
            return rows

        candidates = (
            await db.exec(
                select(AuditOutbox.id)
                .where(reclaimable)
                .order_by(AuditOutbox.created_at.asc())
                .limit(batch_size)
            )
        ).all()
        ids = [row for row in candidates]
        if not ids:
            return []
        await db.exec(
            update(AuditOutbox)
            .where(
                AuditOutbox.id.in_(ids),
                reclaimable,
            )
            .values(
                status=AuditOutboxStatus.PROCESSING,
                locked_at=now,
                locked_by=worker_id,
                updated_at=now,
            )
        )
        await db.commit()
        rows = (
            await db.exec(
                select(AuditOutbox).where(
                    AuditOutbox.id.in_(ids),
                    AuditOutbox.status == AuditOutboxStatus.PROCESSING,
                    AuditOutbox.locked_by == worker_id,
                )
            )
        ).all()
        return rows

    @staticmethod
    async def mark_outbox_done(db: AsyncSession, row: AuditOutbox) -> None:
        now = AuditRepo._utc_now()
        row.status = AuditOutboxStatus.DONE
        row.attempts += 1
        row.locked_at = None
        row.locked_by = None
        row.updated_at = now
        await db.commit()

    @staticmethod
    async def mark_outbox_failed(
        db: AsyncSession,
        row: AuditOutbox,
        *,
        max_retries: int,
    ) -> None:
        now = AuditRepo._utc_now()
        next_attempts = int(row.attempts or 0) + 1
        row.attempts = next_attempts
        row.locked_at = None
        row.locked_by = None
        if next_attempts >= max(1, int(max_retries or 1)):
            row.status = AuditOutboxStatus.FAILED
        else:
            row.status = AuditOutboxStatus.PENDING
        row.updated_at = now
        await db.commit()
