"""
@File: worker.py
@Author: GuaiMiu
@Date: 2026/02/10
@Version: 1.0
@Description: 审计 outbox worker
"""

from __future__ import annotations

import asyncio
import json
import os
from uuid import uuid4

from sqlmodel.ext.asyncio.session import AsyncSession

from app.audit.repo import AuditRepo
from app.core.database import async_session, is_database_configured
from app.modules.system.service.config import build_runtime_config
from app.utils.logger import logger


def _get_worker_id() -> str:
    return os.getenv("AUDIT_WORKER_ID", "") or uuid4().hex


async def _process_batch(
    db: AsyncSession,
    worker_id: str,
    batch_size: int,
    lock_timeout: int,
    max_retries: int,
    retry_delay_seconds: int,
) -> int:
    dialect = db.get_bind().dialect.name
    use_skip_locked = dialect == "mysql"
    rows = await AuditRepo.claim_outbox(
        db,
        batch_size=batch_size,
        worker_id=worker_id,
        lock_timeout_seconds=lock_timeout,
        retry_delay_seconds=retry_delay_seconds,
        use_skip_locked=use_skip_locked,
    )
    if not rows:
        return 0
    processed = 0
    for row in rows:
        try:
            payload = json.loads(row.payload_json)
            await AuditRepo.upsert_log(db, payload)
            await AuditRepo.mark_outbox_done(db, row)
            processed += 1
        except Exception as exc:
            logger.warning("审计 outbox 处理失败: %s", exc)
            await AuditRepo.mark_outbox_failed(
                db,
                row,
                max_retries=max_retries,
            )
    return processed


async def run_forever() -> None:
    if not is_database_configured():
        logger.warning("数据库未配置，跳过审计 worker")
        return
    worker_id = _get_worker_id()
    logger.info("Audit worker started: %s", worker_id)
    while True:
        async with async_session() as session:
            cfg = build_runtime_config(session, request_cache={})
            batch_size = await cfg.audit.outbox_batch_size()
            lock_timeout = await cfg.audit.outbox_lock_timeout_seconds()
            interval = await cfg.audit.outbox_poll_interval_seconds()
            max_retries = await cfg.audit.outbox_max_retries()
            retry_delay = await cfg.audit.outbox_retry_delay_seconds()
            count = await _process_batch(
                session,
                worker_id,
                batch_size=max(int(batch_size or 1), 1),
                lock_timeout=max(int(lock_timeout or 1), 1),
                max_retries=max(int(max_retries or 1), 1),
                retry_delay_seconds=max(int(retry_delay or 1), 1),
            )
        if count == 0:
            await asyncio.sleep(max(float(interval or 1), 0.5))


async def run_once() -> int:
    if not is_database_configured():
        logger.warning("数据库未配置，跳过审计 worker")
        return 0
    worker_id = _get_worker_id()
    async with async_session() as session:
        cfg = build_runtime_config(session, request_cache={})
        batch_size = await cfg.audit.outbox_batch_size()
        lock_timeout = await cfg.audit.outbox_lock_timeout_seconds()
        max_retries = await cfg.audit.outbox_max_retries()
        retry_delay = await cfg.audit.outbox_retry_delay_seconds()
        return await _process_batch(
            session,
            worker_id,
            batch_size=max(int(batch_size or 1), 1),
            lock_timeout=max(int(lock_timeout or 1), 1),
            max_retries=max(int(max_retries or 1), 1),
            retry_delay_seconds=max(int(retry_delay or 1), 1),
        )


def main() -> None:
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
