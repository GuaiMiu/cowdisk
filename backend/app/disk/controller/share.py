"""
@File: share.py
@Author: GuaiMiu
@Date: 2025/4/5 20:26
@Version: 1.0
@Description: 新分享接口
"""

import mimetypes
import re
from datetime import datetime
from email.utils import formatdate
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, Security
from starlette.responses import FileResponse, Response, StreamingResponse

from app.admin.models.response import ResponseModel
from app.admin.models.user import User
from app.admin.services.auth import AuthService, check_user_permission
from app.core.database import get_async_redis, get_async_session
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.exception import ServiceException
from app.disk.schemas.share import (
    ShareCreateIn,
    ShareListOut,
    ShareUnlockIn,
    ShareSaveIn,
    ShareUpdateIn,
)
from app.disk.services.disk import DiskService
from app.disk.services.share import ShareService

share_manage_router = APIRouter(
    prefix="/shares",
    tags=["分享管理"],
    dependencies=[Depends(AuthService.get_current_user_any)],
)

share_public_router = APIRouter(prefix="/public/shares", tags=["公开分享"])


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


def _content_disposition(filename: str, inline: bool) -> str:
    disposition = "inline" if inline else "attachment"
    try:
        filename.encode("latin-1")
        return f'{disposition}; filename="{filename}"'
    except UnicodeEncodeError:
        fallback = "".join(
            char if ord(char) < 128 and char not in {'"', "\\"} else "_"
            for char in filename
        )
        quoted = quote(filename)
        return (
            f'{disposition}; filename="{fallback}"; filename*=UTF-8\'\'{quoted}'
        )


def _iter_file_range(file_path: Path, start: int, end: int, chunk_size: int = 8192):
    with file_path.open("rb") as handle:
        handle.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            read_size = min(chunk_size, remaining)
            data = handle.read(read_size)
            if not data:
                break
            remaining -= len(data)
            yield data


def _build_response(
    request: Request, file_path: Path, filename: str, inline: bool
) -> Response:
    range_header = request.headers.get("range")
    stat = file_path.stat()
    size = stat.st_size
    mtime = int(stat.st_mtime)
    last_modified = formatdate(mtime, usegmt=True)
    etag = f'W/"{size}-{mtime}"'
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(size),
        "Content-Encoding": "identity",
        "ETag": etag,
        "Last-Modified": last_modified,
        "Content-Disposition": _content_disposition(filename, inline=inline),
    }
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    if not range_header:
        return FileResponse(
            file_path,
            filename=filename,
            media_type=media_type if inline else "application/octet-stream",
            headers=headers,
        )

    match = re.match(r"bytes=(\d*)-(\d*)", range_header)
    if not match:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})
    start_str, end_str = match.groups()
    start = int(start_str) if start_str else 0
    end = int(end_str) if end_str else size - 1
    if start >= size or end < start:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})

    headers.update(
        {
            "Content-Range": f"bytes {start}-{end}/{size}",
            "Content-Length": str(end - start + 1),
        }
    )
    return StreamingResponse(
        _iter_file_range(file_path, start, end),
        status_code=206,
        headers=headers,
        media_type=media_type if inline else "application/octet-stream",
    )


@share_manage_router.post(
    "",
    summary="创建分享",
    dependencies=[Security(check_user_permission, scopes=["disk:file:download"])],
)
async def create_share(
    data: ShareCreateIn,
    current_user: User = Depends(AuthService.get_current_user_any),
    db: AsyncSession = Depends(get_async_session),
):
    share = await ShareService.create_share(
        user_id=current_user.id,
        resource_type=data.resourceType,
        path=data.path,
        expires_in_days=data.expiresInDays,
        expires_at=data.expiresAt,
        code=data.code,
        db=db,
    )
    return ResponseModel.success(data=share)


@share_manage_router.get(
    "",
    summary="分享列表",
    response_model=ResponseModel[ShareListOut],
    dependencies=[Security(check_user_permission, scopes=["disk:file:download"])],
)
async def list_shares(
    keyword: str | None = None,
    status: str | None = None,
    page: int = 1,
    size: int = 20,
    current_user: User = Depends(AuthService.get_current_user_any),
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
    return ResponseModel.success(
        data={"items": items, "total": total, "page": page, "size": page_size, "pages": pages}
    )


@share_manage_router.post(
    "/{share_id}/revoke",
    summary="取消分享",
    dependencies=[Security(check_user_permission, scopes=["disk:file:download"])],
)
async def revoke_share(
    share_id: str,
    current_user: User = Depends(AuthService.get_current_user_any),
    db: AsyncSession = Depends(get_async_session),
):
    await ShareService.revoke_share(current_user.id, share_id, db)
    return ResponseModel.success(data=True)


@share_manage_router.put(
    "/{share_id}",
    summary="更新分享",
    dependencies=[Security(check_user_permission, scopes=["disk:file:download"])],
)
async def update_share(
    share_id: str,
    data: ShareUpdateIn,
    current_user: User = Depends(AuthService.get_current_user_any),
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
    return ResponseModel.success(data=share)


@share_manage_router.delete(
    "/{share_id}",
    summary="删除分享",
    dependencies=[Security(check_user_permission, scopes=["disk:file:download"])],
)
async def delete_share(
    share_id: str,
    current_user: User = Depends(AuthService.get_current_user_any),
    db: AsyncSession = Depends(get_async_session),
):
    await ShareService.delete_share(current_user.id, share_id, db)
    return ResponseModel.success(data=True)


@share_public_router.get("/{token}", summary="获取公开分享")
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
    file_meta = None
    if share.get("resourceType") == "FILE":
        try:
            file_path = await ShareService.download_share_file(share, user_id, None)
            file_meta = {
                "size": file_path.stat().st_size,
                "mime": mimetypes.guess_type(file_path.name)[0]
                or "application/octet-stream",
            }
        except Exception:
            file_meta = None
    return ResponseModel.success(
        data={"locked": False, "share": share_public, "fileMeta": file_meta}
    )


@share_public_router.post("/{token}/unlock", summary="解锁分享")
async def unlock_share(
    token: str,
    data: ShareUnlockIn,
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    user_id, share = await ShareService.resolve_share(token, db)
    if not share.get("hasCode"):
        return ResponseModel.success(data={"ok": True})
    if data.code != share.get("code"):
        raise ServiceException(msg="提取码错误")
    access_token = uuid4().hex
    ttl = 86400 * 7
    expires_at = share.get("expiresAt")
    if expires_at:
        ttl = max(int((int(expires_at) - DiskService._to_ms(datetime.utcnow())) / 1000), 60)
    await redis.set(ShareService.share_access_key(token, access_token), "1", ex=ttl)
    return ResponseModel.success(data={"accessToken": access_token})


@share_public_router.get("/{token}/list", summary="分享目录列表")
async def list_share_entries(
    token: str,
    request: Request,
    path: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    user_id, share = await ShareService.resolve_share(token, db)
    if share.get("hasCode"):
        access_token = _get_access_token(request)
        if not access_token:
            raise ServiceException(msg="需要提取码")
        ok = await redis.get(ShareService.share_access_key(token, access_token))
        if not ok:
            raise ServiceException(msg="需要提取码")
    items = await ShareService.list_share_entries(share, user_id, path)
    offset = int(cursor) if cursor and cursor.isdigit() else 0
    end = offset + max(1, min(limit, 100))
    next_cursor = str(end) if end < len(items) else None
    return ResponseModel.success(
        data={"items": items[offset:end], "nextCursor": next_cursor}
    )


@share_public_router.get("/{token}/download", summary="分享文件下载")
async def download_share(
    token: str,
    request: Request,
    path: str | None = None,
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    user_id, share = await ShareService.resolve_share(token, db)
    if share.get("hasCode"):
        access_token = _get_access_token(request)
        if not access_token:
            raise ServiceException(msg="需要提取码")
        ok = await redis.get(ShareService.share_access_key(token, access_token))
        if not ok:
            raise ServiceException(msg="需要提取码")
    file_path = await ShareService.download_share_file(share, user_id, path)
    return _build_response(request, file_path, file_path.name, inline=False)


@share_public_router.get("/{token}/preview", summary="分享文件预览")
async def preview_share(
    token: str,
    request: Request,
    path: str | None = None,
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    user_id, share = await ShareService.resolve_share(token, db)
    if share.get("hasCode"):
        access_token = _get_access_token(request)
        if not access_token:
            raise ServiceException(msg="需要提取码")
        ok = await redis.get(ShareService.share_access_key(token, access_token))
        if not ok:
            raise ServiceException(msg="需要提取码")
    file_path = await ShareService.download_share_file(share, user_id, path)
    return _build_response(request, file_path, file_path.name, inline=True)


@share_public_router.post("/{token}/save", summary="保存到我的网盘")
async def save_share(
    token: str,
    data: ShareSaveIn,
    current_user: User = Depends(AuthService.get_current_user_any),
    db: AsyncSession = Depends(get_async_session),
):
    owner_id, share = await ShareService.resolve_share(token, db)
    await ShareService.save_share_to_user(
        share=share,
        owner_id=owner_id,
        target_user_id=current_user.id,
        target_path=data.targetPath,
    )
    return ResponseModel.success(data=True)
