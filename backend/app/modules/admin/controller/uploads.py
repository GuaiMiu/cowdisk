"""
@File: uploads.py
@Author: GuaiMiu
@Date: 2026/2/7
@Version: 1.0
@Description: 上传会话管理
"""

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_redis, get_async_session
from app.core.response import ApiResponse, ok
from app.modules.disk.services.file import FileService
from app.shared.deps import require_permissions, require_user

admin_upload_router = APIRouter(
    prefix="/uploads",
    tags=["Admin - Uploads"],
    dependencies=[Depends(require_user)],
)


@admin_upload_router.post(
    "/gc",
    summary="上传会话GC",
    response_model=ApiResponse[dict],
    dependencies=[require_permissions(["cfg:upload:operate"])],
)
async def gc_upload_sessions(
    dry_run: bool = Query(False),
    db: AsyncSession = Depends(get_async_session),
    redis=Depends(get_async_redis),
):
    result = await FileService.gc_uploads(db=db, redis=redis, dry_run=dry_run)
    return ok(result)
