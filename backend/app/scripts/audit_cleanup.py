"""
@File: audit_cleanup.py
@Author: GuaiMiu
@Date: 2026/02/10
@Version: 1.0
@Description: 审计日志清理脚本
"""

import asyncio

from app.audit.usecase import AuditUsecase
from app.core.database import async_session
from app.modules.system.service.config import build_runtime_config


async def main():
    async with async_session() as session:
        cfg = build_runtime_config(session, request_cache={})
        retention_days = await cfg.audit.retention_days()
        deleted = await AuditUsecase.cleanup_logs(
            db=session, retention_days=int(retention_days or 90), commit=True
        )
    print(f"Deleted audit logs: {deleted}")


if __name__ == "__main__":
    asyncio.run(main())

