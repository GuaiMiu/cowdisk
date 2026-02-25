"""
@File: public_shares.py
@Author: GuaiMiu
@Date: 2026/2/7
@Version: 1.0
@Description: 公开分享新接口
"""

from fastapi import APIRouter, Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_redis, get_async_session
from app.core.response import ApiResponse, ok
from app.modules.admin.models.user import User
from app.modules.disk.schemas.share import ShareSaveIn, ShareUnlockIn
from app.modules.disk.services.share import ShareService
from app.shared.deps import require_user

public_shares_router = APIRouter(prefix="/shares", tags=["Disk - Public Share"])


@public_shares_router.get("/{token}", summary="获取公开分享", response_model=ApiResponse[dict])
async def get_public_share(
    token: str,
    request: Request,
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    data = await ShareService.get_public_share_detail(
        token=token,
        request=request,
        redis=redis,
        db=db,
    )
    return ok(data)


@public_shares_router.post("/{token}/unlock", summary="解锁分享", response_model=ApiResponse[dict])
async def unlock_share(
    token: str,
    data: ShareUnlockIn,
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    result = await ShareService.unlock_public_share(
        token=token,
        code=data.code,
        redis=redis,
        db=db,
    )
    return ok(result)


@public_shares_router.get("/{token}/entries", summary="分享目录列表", response_model=ApiResponse[dict])
async def list_share_entries(
    token: str,
    request: Request,
    parent_id: int | None = None,
    cursor: str | None = None,
    limit: int = 50,
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    data = await ShareService.list_public_share_entries_page(
        token=token,
        request=request,
        redis=redis,
        db=db,
        parent_id=parent_id,
        cursor=cursor,
        limit=limit,
    )
    return ok(data)


@public_shares_router.get("/{token}/content", summary="分享文件内容")
async def get_share_content(
    token: str,
    request: Request,
    file_id: int | None = None,
    disposition: str = "attachment",
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    return await ShareService.get_public_share_content_response(
        token=token,
        request=request,
        redis=redis,
        db=db,
        file_id=file_id,
        disposition=disposition,
    )


@public_shares_router.post("/{token}/save", summary="保存到我的网盘", response_model=ApiResponse[bool])
async def save_share(
    token: str,
    data: ShareSaveIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    await ShareService.save_public_share_to_user_with_refresh(
        token=token,
        target_user_id=current_user.id,
        target_parent_id=data.targetParentId,
        db=db,
    )
    return ok(True)
