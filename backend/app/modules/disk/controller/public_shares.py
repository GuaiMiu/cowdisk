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
from app.modules.admin.models.response import ResponseModel
from app.modules.admin.models.user import User
from app.shared.deps import require_user
from app.core.database import get_async_redis, get_async_session
from app.core.exception import ServiceException
from app.modules.disk.schemas.share import ShareSaveIn, ShareUnlockIn
from app.modules.disk.services.file import FileService
from app.modules.disk.services.share import ShareService
from sqlmodel.ext.asyncio.session import AsyncSession

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


@public_shares_router.get("/{token}", summary="获取公开分享")
async def get_public_share(
    token: str,
    request: Request,
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    """
    获取公开分享的基础信息。
    若分享设置提取码则返回 locked=true。
    提取码验证通过后返回完整分享信息。
    不需要用户登录即可访问。
    锁定状态仅暴露最小字段集。
    幂等：相同 token 返回一致结果。
    性能：单次 DB 查询 + Redis 校验。
    返回：分享信息与锁定状态。
    """
    user_id, share = await ShareService.resolve_share(token, db)
    if share.get("hasCode"):
        access_token = _get_access_token(request)
        if access_token:
            key = ShareService.share_access_key(token, access_token)
            ok = await redis.get(key)
            if not ok:
                return ResponseModel.success(
                    data={
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
            return ResponseModel.success(
                data={
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
    return ResponseModel.success(
        data={"locked": False, "share": share_public, "fileMeta": file_meta}
    )


@public_shares_router.post("/{token}/unlock", summary="解锁分享")
async def unlock_share(
    token: str,
    data: ShareUnlockIn,
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    """
    校验提取码并发放访问 token。
    accessToken 存储在 Redis，具备过期时间。
    若分享无提取码则直接返回 ok。
    过期时间优先遵循分享过期配置。
    幂等：重复解锁会生成新 accessToken。
    仅用于公开分享，非登录态接口。
    错误：提取码不匹配则返回错误。
    返回：accessToken 或 ok。
    """
    user_id, share = await ShareService.resolve_share(token, db)
    if not share.get("hasCode"):
        return ResponseModel.success(data={"ok": True})
    if data.code != share.get("code"):
        raise ServiceException(msg="提取码错误")
    access_token = uuid4().hex
    ttl = 86400 * 7
    expires_at = share.get("expiresAt")
    if expires_at:
        ttl = max(
            int((int(expires_at) - ShareService._to_ms(datetime.now())) / 1000),
            60,
        )
    await redis.set(ShareService.share_access_key(token, access_token), "1", ex=ttl)
    return ResponseModel.success(data={"accessToken": access_token})


@public_shares_router.get("/{token}/entries", summary="分享目录列表")
async def list_share_entries(
    token: str,
    request: Request,
    parent_id: int | None = None,
    cursor: str | None = None,
    limit: int = 50,
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    """
    获取分享目录内容列表。
    通过 cursor/limit 实现简易分页。
    若分享设置提取码需先解锁。
    仅允许在分享范围内访问内容。
    幂等：同参数返回一致结果。
    性能：先拉取全量后再裁剪。
    错误：未解锁或无权限时返回错误。
    返回：items 与 nextCursor。
    """
    user_id, share = await ShareService.resolve_share(token, db)
    if share.get("hasCode"):
        access_token = _get_access_token(request)
        if not access_token:
            raise ServiceException(msg="需要提取码")
        ok = await redis.get(ShareService.share_access_key(token, access_token))
        if not ok:
            raise ServiceException(msg="需要提取码")
    items = await ShareService.list_share_entries(share, user_id, db, parent_id)
    offset = int(cursor) if cursor and cursor.isdigit() else 0
    end = offset + max(1, min(limit, 100))
    next_cursor = str(end) if end < len(items) else None
    return ResponseModel.success(
        data={"items": items[offset:end], "nextCursor": next_cursor}
    )


@public_shares_router.get("/{token}/content", summary="分享文件内容")
async def get_share_content(
    token: str,
    request: Request,
    file_id: int | None = None,
    disposition: str = "attachment",
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    """
    下载/预览公开分享中的文件。
    disposition=inline 时以预览方式返回。
    """
    user_id, share = await ShareService.resolve_share(token, db)
    if share.get("hasCode"):
        access_token = _get_access_token(request)
        if not access_token:
            raise ServiceException(msg="需要提取码")
        ok = await redis.get(ShareService.share_access_key(token, access_token))
        if not ok:
            raise ServiceException(msg="需要提取码")
    file_path = await ShareService.download_share_file(share, user_id, db, file_id)
    return FileService.build_download_response(
        request=request,
        file_path=file_path,
        filename=file_path.name,
        inline=disposition == "inline",
        background=None,
    )


@public_shares_router.post("/{token}/save", summary="保存到我的网盘")
async def save_share(
    token: str,
    data: ShareSaveIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    将分享内容保存到当前用户网盘。
    需要登录态并具备上传权限。
    保存后会创建新的文件条目。
    不改变分享源文件。
    并发：多用户保存互不影响。
    错误：权限不足或目标冲突将报错。
    性能：依赖后台复制/写入开销。
    返回：成功布尔值。
    """
    owner_id, share = await ShareService.resolve_share(token, db)
    await ShareService.save_share_to_user(
        share=share,
        owner_id=owner_id,
        target_user_id=current_user.id,
        target_parent_id=data.targetParentId,
        db=db,
    )
    return ResponseModel.success(data=True)
