"""
@File: uploads.py
@Author: GuaiMiu
@Date: 2026/2/7
@Version: 1.0
@Description: 上传会话管理
"""

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.admin.models.response import ResponseModel
from app.shared.deps import require_permissions, require_user
from app.core.database import get_async_session
from app.modules.disk.services.file import FileService

admin_upload_router = APIRouter(
    prefix="/uploads",
    tags=["Admin - Uploads"],
    dependencies=[Depends(require_user)],
)


@admin_upload_router.post(
    "/gc",
    summary="上传会话GC",
    dependencies=[require_permissions(["cfg:upload:operate"])],
)
async def gc_upload_sessions(
    dry_run: bool = Query(False),
    db: AsyncSession = Depends(get_async_session),
):
    result = await FileService.gc_uploads(db=db, dry_run=dry_run)
    return ResponseModel.success(data=result)



