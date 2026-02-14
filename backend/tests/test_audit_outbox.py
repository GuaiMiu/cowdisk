from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.audit.constants import AuditOutboxStatus
from app.audit.models import AuditOutbox
from app.audit.repo import AuditRepo


@pytest_asyncio.fixture
async def db_session(tmp_path: Path):
    db_path = tmp_path / "test_audit_outbox.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_mark_outbox_failed_requeue_then_failed(db_session: AsyncSession):
    row = AuditOutbox(
        event_type="AUDIT",
        payload_json="{}",
        status=AuditOutboxStatus.PROCESSING,
        attempts=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        locked_at=datetime.now(timezone.utc),
        locked_by="worker-1",
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)

    await AuditRepo.mark_outbox_failed(db_session, row, max_retries=3)
    assert row.status == AuditOutboxStatus.PENDING
    assert row.attempts == 1
    assert row.locked_by is None
    assert row.locked_at is None

    await AuditRepo.mark_outbox_failed(db_session, row, max_retries=2)
    assert row.status == AuditOutboxStatus.FAILED
    assert row.attempts == 2


@pytest.mark.asyncio
async def test_claim_outbox_reclaims_stuck_processing(db_session: AsyncSession):
    now = datetime.now(timezone.utc)
    row = AuditOutbox(
        event_type="AUDIT",
        payload_json="{}",
        status=AuditOutboxStatus.PROCESSING,
        attempts=0,
        created_at=now - timedelta(minutes=2),
        updated_at=now - timedelta(minutes=2),
        locked_at=now - timedelta(minutes=2),
        locked_by="dead-worker",
    )
    db_session.add(row)
    await db_session.commit()

    rows = await AuditRepo.claim_outbox(
        db_session,
        batch_size=10,
        worker_id="live-worker",
        lock_timeout_seconds=30,
        retry_delay_seconds=1,
        use_skip_locked=False,
    )
    assert len(rows) == 1
    assert rows[0].status == AuditOutboxStatus.PROCESSING
    assert rows[0].locked_by == "live-worker"
