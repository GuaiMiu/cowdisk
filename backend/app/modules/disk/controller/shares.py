"""
@File: shares.py
@Author: GuaiMiu
@Date: 2026/2/7
@Version: 1.0
@Description: 分享管理新接口
"""

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_session
from app.core.response import ApiResponse, ok
from app.modules.admin.models.user import User
from app.modules.disk.schemas.share import (
    ShareBatchIdsIn,
    ShareBatchStatusIn,
    ShareCreateIn,
    ShareListOut,
    ShareUpdateIn,
)
from app.modules.disk.services.share import ShareService
from app.shared.deps import require_permissions, require_user

shares_router = APIRouter(
    prefix="/shares",
    tags=["Disk - Share"],
    dependencies=[Depends(require_user)],
)


@shares_router.post(
    "",
    summary="创建分享",
    response_model=ApiResponse[dict],
    dependencies=[require_permissions(["disk:share:create"])],
)
async def create_share(
    data: ShareCreateIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    share = await ShareService.create_share(
        user_id=current_user.id,
        file_id=data.fileId,
        expires_in_days=data.expiresInDays,
        expires_at=data.expiresAt,
        code=data.code,
        db=db,
    )
    return ok(share, message="创建成功")


@shares_router.get(
    "",
    summary="分享列表",
    response_model=ApiResponse[ShareListOut],
    dependencies=[require_permissions(["disk:share:list"])],
)
async def list_shares(
    keyword: str | None = None,
    status: str | None = None,
    page: int = 1,
    size: int = 20,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    items, total, pages, page_size = await ShareService.list_shares(
        user_id=current_user.id,
        keyword=keyword,
        status=status,
        page=max(1, page),
        size=max(1, min(size, 100)),
        db=db,
    )
    return ok(
        ShareListOut(
            items=items,
            total=total,
            page=page,
            size=page_size,
            pages=pages,
        ).model_dump()
    )


@shares_router.post(
    "/batch/status",
    summary="批量更新分享状态",
    response_model=ApiResponse[dict],
    dependencies=[require_permissions(["disk:share:update"])],
)
async def batch_update_status(
    data: ShareBatchStatusIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    result = await ShareService.batch_update_status(
        current_user.id, data.ids, data.status, db
    )
    return ok(result, message="更新成功")


@shares_router.put(
    "/{share_id}",
    summary="更新分享",
    response_model=ApiResponse[dict],
    dependencies=[require_permissions(["disk:share:update"])],
)
async def update_share(
    share_id: str,
    data: ShareUpdateIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    share = await ShareService.update_share(
        user_id=current_user.id,
        share_id=share_id,
        expires_in_days=data.expiresInDays,
        expires_at=data.expiresAt,
        code=data.code,
        status=data.status,
        db=db,
    )
    return ok(share, message="更新成功")


@shares_router.post(
    "/batch/delete",
    summary="批量删除分享",
    response_model=ApiResponse[dict],
    dependencies=[require_permissions(["disk:share:delete"])],
)
async def batch_delete_share(
    data: ShareBatchIdsIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    result = await ShareService.batch_delete(current_user.id, data.ids, db)
    return ok(result, message="删除完成")


@shares_router.delete(
    "/{share_id}",
    summary="删除分享",
    response_model=ApiResponse[bool],
    dependencies=[require_permissions(["disk:share:delete"])],
)
async def delete_share(
    share_id: str,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    await ShareService.delete_share(current_user.id, share_id, db)
    return ok(True, message="删除成功")
