"""
@File: trash.py
@Author: GuaiMiu
@Date: 2026/2/7
@Version: 1.0
@Description: 回收站新接口
"""

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_session
from app.core.response import ApiResponse, ok
from app.modules.admin.models.user import User
from app.modules.disk.schemas.disk import (
    DiskTrashBatchIdsIn,
    DiskTrashBatchOut,
    DiskTrashDeleteIn,
    DiskTrashListOut,
    DiskTrashRestoreIn,
    FileEntryOut,
)
from app.modules.disk.services.file import FileService
from app.shared.deps import require_permissions, require_user

trash_router = APIRouter(
    prefix="/trash",
    tags=["Disk - Trash"],
    dependencies=[Depends(require_user)],
)


@trash_router.get(
    "",
    summary="回收站列表",
    response_model=ApiResponse[DiskTrashListOut],
    dependencies=[require_permissions(["disk:trash:list"])],
)
async def list_trash(
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    data = await FileService.list_trash(current_user.id, db)
    return ok(data)


@trash_router.post(
    "/restore",
    summary="恢复回收站条目",
    response_model=ApiResponse[FileEntryOut],
    dependencies=[require_permissions(["disk:trash:restore"])],
)
async def restore_trash(
    data: DiskTrashRestoreIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    entry = await FileService.restore_trash(int(data.id), current_user.id, db)
    await FileService.refresh_used_space(db, current_user.id)
    return ok(entry.model_dump())


@trash_router.post(
    "/batch/restore",
    summary="批量恢复回收站条目",
    response_model=ApiResponse[DiskTrashBatchOut],
    dependencies=[require_permissions(["disk:trash:restore"])],
)
async def batch_restore_trash(
    data: DiskTrashBatchIdsIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    ids = [int(value) for value in data.ids]
    result = await FileService.batch_restore_trash(ids, current_user.id, db)
    if result.get("success"):
        await FileService.refresh_used_space(db, current_user.id)
    return ok(result)


@trash_router.post(
    "/batch/delete",
    summary="批量彻底删除回收站条目",
    response_model=ApiResponse[DiskTrashBatchOut],
    dependencies=[require_permissions(["disk:trash:delete"])],
)
async def batch_delete_trash(
    data: DiskTrashBatchIdsIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    ids = [int(value) for value in data.ids]
    result = await FileService.batch_delete_trash(ids, current_user.id, db)
    return ok(result)


@trash_router.delete(
    "",
    summary="彻底删除回收站条目",
    response_model=ApiResponse[bool],
    dependencies=[require_permissions(["disk:trash:delete"])],
)
async def delete_trash(
    data: DiskTrashDeleteIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    result = await FileService.delete_trash(int(data.id), current_user.id, db)
    return ok(result)


@trash_router.delete(
    "/clear",
    summary="清空回收站",
    response_model=ApiResponse[dict],
    dependencies=[require_permissions(["disk:trash:clear"])],
)
async def clear_trash(
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    count = await FileService.clear_trash(current_user.id, db)
    return ok({"cleared": count})
