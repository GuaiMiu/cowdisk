"""
@File: access.py
@Author: GuaiMiu
@Date: 2026/2/10
@Version: 1.0
@Description: 下载/预览 Token 接口
"""

from fastapi import APIRouter, Depends, Request
from redis import asyncio as aioredis
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_redis, get_async_session
from app.modules.admin.models.response import ResponseModel
from app.modules.admin.models.user import User
from app.modules.disk.services.file import FileService
from app.modules.disk.services.office import OfficeService
from app.shared.deps import require_permissions, require_user

access_router = APIRouter(prefix="/files", tags=["Disk - Access"])


@access_router.post(
    "/{file_id}/download-url",
    summary="签发下载 URL",
    response_model=ResponseModel[dict],
    dependencies=[require_permissions(["disk:file:download"])],
)
async def issue_download_url(
    request: Request,
    file_id: int,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_async_redis),
):
    data = await FileService.issue_download_url(
        request=request,
        db=db,
        file_id=file_id,
        user_id=current_user.id,
        redis=redis,
    )
    return ResponseModel.success(data=data)


@access_router.post(
    "/{file_id}/preview-url",
    summary="签发预览 URL",
    response_model=ResponseModel[dict],
    dependencies=[require_permissions(["disk:file:download"])],
)
async def issue_preview_url(
    request: Request,
    file_id: int,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_async_redis),
):
    data = await FileService.issue_preview_url(
        request=request,
        db=db,
        file_id=file_id,
        user_id=current_user.id,
        redis=redis,
    )
    return ResponseModel.success(data=data)


@access_router.post(
    "/{file_id}/office-url",
    summary="签发 Office 打开 URL",
    response_model=ResponseModel[dict],
    dependencies=[require_permissions(["disk:file:download"])],
)
async def issue_office_url(
    request: Request,
    file_id: int,
    lang: str | None = None,
    mode: str | None = None,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_async_redis),
):
    data = await OfficeService.issue_office_url(
        request=request,
        db=db,
        file_id=file_id,
        user_id=current_user.id,
        redis=redis,
        lang=lang,
        mode=mode,
    )
    return ResponseModel.success(data=data)


@access_router.get("/{file_id}/download", summary="下载文件(下载令牌)")
async def download_by_token(
    request: Request,
    file_id: int,
    token: str,
    db: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_async_redis),
):
    return await FileService.download_file(
        request=request,
        db=db,
        file_id=file_id,
        token=token,
        redis=redis,
    )


@access_router.get("/{file_id}/preview", summary="预览文件(预览令牌)")
async def preview_by_token(
    request: Request,
    file_id: int,
    token: str,
    db: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_async_redis),
):
    return await FileService.preview_file(
        request=request,
        db=db,
        file_id=file_id,
        token=token,
        redis=redis,
    )
