"""
@File: router.py
@Author: GuaiMiu
@Date: 2026/02/10
@Version: 1.0
@Description: 审计日志接口
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, time

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.audit.usecase import AuditUsecase
from app.core.database import get_async_session
from app.modules.admin.models.response import ResponseModel
from app.modules.system.deps import get_config
from app.modules.system.schemas.audit import (
    AuditLogListOut,
    AuditLogQueryParams,
    AuditLogItem,
)
from app.modules.system.typed.config import Config
from app.shared.deps import require_permissions, require_user


audit_router = APIRouter(
    prefix="/audit",
    tags=["System - Audit"],
    dependencies=[Depends(require_user)],
)


def _normalize_range(
    start: datetime | None, end: datetime | None
) -> tuple[datetime | None, datetime | None]:
    if start and start.time() == time.min:
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    if end and end.time() == time.min:
        end = end + timedelta(days=1) - timedelta(microseconds=1)
    return start, end


@audit_router.get(
    "/logs",
    summary="获取审计日志",
    response_model=ResponseModel[AuditLogListOut],
    dependencies=[require_permissions(["cfg:audit:read"])],
)
async def list_audit_logs(
    params: AuditLogQueryParams = Depends(),
    db: AsyncSession = Depends(get_async_session),
):
    start, end = _normalize_range(params.start, params.end)
    total, items = await AuditUsecase.list_logs(
        db=db,
        start=start,
        end=end,
        user_id=params.user_id,
        action=params.action,
        status=params.status,
        keyword=params.q,
        page=max(params.page, 1),
        page_size=max(min(params.page_size, 200), 1),
    )
    data = AuditLogListOut(
        total=total,
        items=[AuditLogItem.model_validate(item, from_attributes=True) for item in items],
    )
    return ResponseModel.success(data=data)


@audit_router.get(
    "/logs/export",
    summary="导出审计日志",
    dependencies=[require_permissions(["cfg:audit:operate"])],
)
async def export_audit_logs(
    params: AuditLogQueryParams = Depends(),
    db: AsyncSession = Depends(get_async_session),
    config: Config = Depends(get_config),
):
    max_rows = min(int(await config.audit.export_max_rows() or 50000), 200000)
    start, end = _normalize_range(params.start, params.end)
    if not start and not end:
        end = datetime.now()
        start = end - timedelta(days=7)
    _, items = await AuditUsecase.export_logs(
        db=db,
        start=start,
        end=end,
        user_id=params.user_id,
        action=params.action,
        status=params.status,
        keyword=params.q,
        page_size=max_rows,
        page=1,
        commit=False,
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["id", "created_at", "user_id", "action", "status", "path", "ip", "detail"]
    )
    for item in items:
        writer.writerow(
            [
                item.id,
                item.created_at.isoformat(),
                item.user_id,
                item.action,
                item.status,
                item.path,
                item.ip,
                item.detail or "",
            ]
        )
    data = output.getvalue().encode("utf-8-sig")
    start_label = start.date().isoformat() if start else "all"
    end_label = end.date().isoformat() if end else "all"
    filename = f"audit_{start_label}_{end_label}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(io.BytesIO(data), media_type="text/csv", headers=headers)


@audit_router.post(
    "/cleanup",
    summary="清理审计日志",
    response_model=ResponseModel[dict],
    dependencies=[require_permissions(["cfg:audit:operate"])],
)
async def cleanup_audit_logs(
    db: AsyncSession = Depends(get_async_session),
    config: Config = Depends(get_config),
):
    retention = int(await config.audit.retention_days() or 90)
    deleted = await AuditUsecase.cleanup_logs(
        db=db,
        retention_days=retention,
    )
    return ResponseModel.success(data={"deleted": deleted})
