"""
@File: public_shares.py
@Author: GuaiMiu
@Date: 2026/2/7
@Version: 1.0
@Description: 公开分享新接口
"""

import re
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_redis, get_async_session
from app.core.errors.exceptions import ShareCodeInvalid, ShareCodeRequired
from app.core.response import ApiResponse, ok
from app.modules.admin.models.user import User
from app.modules.disk.schemas.share import ShareSaveIn, ShareUnlockIn
from app.modules.disk.services.file import FileService
from app.modules.disk.services.share import ShareService
from app.shared.deps import require_user

public_shares_router = APIRouter(prefix="/shares", tags=["Disk - Public Share"])


def _get_access_token(request: Request) -> str | None:
    query_token = request.query_params.get("accessToken")
    if query_token:
        return query_token
    auth = request.headers.get("authorization")
    if not auth:
        return None
    match = re.match(r"Bearer\s+(.+)", auth, re.IGNORECASE)
    if not match:
        return None
    return match.group(1)


@public_shares_router.get("/{token}", summary="获取公开分享", response_model=ApiResponse[dict])
async def get_public_share(
    token: str,
    request: Request,
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    user_id, share = await ShareService.resolve_share(token, db)
    if share.get("hasCode"):
        access_token = _get_access_token(request)
        if access_token:
            key = ShareService.share_access_key(token, access_token)
            valid = await redis.get(key)
            if not valid:
                return ok(
                    {
                        "locked": True,
                        "share": {
                            "name": share.get("name"),
                            "resourceType": share.get("resourceType"),
                            "expiresAt": share.get("expiresAt"),
                            "ownerName": share.get("ownerName"),
                        },
                    }
                )
        else:
            return ok(
                {
                    "locked": True,
                    "share": {
                        "name": share.get("name"),
                        "resourceType": share.get("resourceType"),
                        "expiresAt": share.get("expiresAt"),
                        "ownerName": share.get("ownerName"),
                    },
                }
            )
    share_public = dict(share)
    share_public.pop("code", None)
    file_meta = await ShareService.get_share_file_meta(share, user_id, db)
    return ok({"locked": False, "share": share_public, "fileMeta": file_meta})


@public_shares_router.post("/{token}/unlock", summary="解锁分享", response_model=ApiResponse[dict])
async def unlock_share(
    token: str,
    data: ShareUnlockIn,
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    _, share = await ShareService.resolve_share(token, db)
    if not share.get("hasCode"):
        return ok({"ok": True})
    if data.code != share.get("code"):
        raise ShareCodeInvalid()
    access_token = uuid4().hex
    ttl = 86400 * 7
    expires_at = share.get("expiresAt")
    if expires_at:
        ttl = max(
            int((int(expires_at) - ShareService._to_ms(datetime.now())) / 1000),
            60,
        )
    await redis.set(ShareService.share_access_key(token, access_token), "1", ex=ttl)
    return ok({"accessToken": access_token})


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
    user_id, share = await ShareService.resolve_share(token, db)
    if share.get("hasCode"):
        access_token = _get_access_token(request)
        if not access_token:
            raise ShareCodeRequired()
        valid = await redis.get(ShareService.share_access_key(token, access_token))
        if not valid:
            raise ShareCodeRequired()
    items = await ShareService.list_share_entries(share, user_id, db, parent_id)
    offset = int(cursor) if cursor and cursor.isdigit() else 0
    end = offset + max(1, min(limit, 100))
    next_cursor = str(end) if end < len(items) else None
    return ok({"items": items[offset:end], "nextCursor": next_cursor})


@public_shares_router.get("/{token}/content", summary="分享文件内容")
async def get_share_content(
    token: str,
    request: Request,
    file_id: int | None = None,
    disposition: str = "attachment",
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    user_id, share = await ShareService.resolve_share(token, db)
    if share.get("hasCode"):
        access_token = _get_access_token(request)
        if not access_token:
            raise ShareCodeRequired()
        valid = await redis.get(ShareService.share_access_key(token, access_token))
        if not valid:
            raise ShareCodeRequired()
    file_path = await ShareService.download_share_file(share, user_id, db, file_id)
    return FileService.build_download_response(
        request=request,
        file_path=file_path,
        filename=file_path.name,
        inline=disposition == "inline",
        background=None,
    )


@public_shares_router.post("/{token}/save", summary="保存到我的网盘", response_model=ApiResponse[bool])
async def save_share(
    token: str,
    data: ShareSaveIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    owner_id, share = await ShareService.resolve_share(token, db)
    await ShareService.save_share_to_user(
        share=share,
        owner_id=owner_id,
        target_user_id=current_user.id,
        target_parent_id=data.targetParentId,
        db=db,
    )
    await FileService.refresh_used_space(db, current_user.id)
    return ok(True)
