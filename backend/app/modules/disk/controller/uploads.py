"""
@File: uploads.py
@Author: GuaiMiu
@Date: 2026/2/7
@Version: 1.0
@Description: 分片上传新接口
"""

from typing import Any, Awaitable, Callable

from fastapi import APIRouter, Depends, File, UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_redis, get_async_session
from app.core.errors.exceptions import BadRequestException
from app.core.response import ApiResponse, ok
from app.modules.admin.models.user import User
from app.modules.disk.domain.paths import rel_path_from_storage
from app.modules.disk.schemas.disk import (
    DiskUploadFinalizeIn,
    DiskUploadInitIn,
    DiskUploadInitOut,
    DiskUploadStatusOut,
    FileEntryOut,
)
from app.modules.disk.services.file import FileService
from app.modules.system.deps import get_config
from app.modules.system.typed.config import Config
from app.shared.deps import require_permissions, require_user

uploads_router = APIRouter(
    prefix="/uploads",
    tags=["Disk - Upload"],
    dependencies=[Depends(require_user)],
)


async def _with_config(
    config: Config,
    fn: Callable[..., Awaitable[Any]],
    *args: Any,
    **kwargs: Any,
) -> Any:
    token = FileService.bind_config(config)
    try:
        return await fn(*args, **kwargs)
    finally:
        FileService.unbind_config(token)


async def _build_upload_policy(config: Config) -> dict[str, Any]:
    return {
        "chunk_size_mb": await config.upload.chunk_size_mb(),
        "chunk_upload_threshold_mb": await config.upload.chunk_upload_threshold_mb(),
        "max_parallel_chunks": await config.upload.max_parallel_chunks(),
        "max_concurrency_per_user": await config.upload.max_concurrency_per_user(),
        "chunk_retry_max": await config.upload.chunk_retry_max(),
        "chunk_retry_base_ms": await config.upload.chunk_retry_base_ms(),
        "chunk_retry_max_ms": await config.upload.chunk_retry_max_ms(),
        "enable_resumable": await config.upload.enable_resumable(),
        "max_single_file_mb": await config.upload.max_single_file_mb(),
    }


@uploads_router.post(
    "",
    summary="初始化分片上传",
    response_model=ApiResponse[DiskUploadInitOut],
    dependencies=[require_permissions(["disk:upload:init"])],
)
async def init_upload(
    data: DiskUploadInitIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
    redis=Depends(get_async_redis),
    config: Config = Depends(get_config),
):
    result = await _with_config(
        config,
        FileService.init_upload_session,
        db=db,
        redis=redis,
        user_id=current_user.id,
        parent_id=data.parent_id,
        name=data.name,
        size=data.size,
        part_size=data.part_size,
        overwrite=data.overwrite,
    )
    upload_config = await _build_upload_policy(config)
    return ok(DiskUploadInitOut(**result, upload_config=upload_config).model_dump())


@uploads_router.get(
    "/policy",
    summary="获取上传策略",
    response_model=ApiResponse[dict],
    dependencies=[require_permissions(["disk:upload:init"])],
)
async def get_upload_policy(config: Config = Depends(get_config)):
    data = await _build_upload_policy(config)
    return ok(data)


@uploads_router.put(
    "/{upload_id}/parts/{part_number}",
    summary="上传分片",
    response_model=ApiResponse[bool],
    dependencies=[require_permissions(["disk:upload:part"])],
)
async def upload_part(
    upload_id: str,
    part_number: int,
    chunk: UploadFile = File(...),
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
    config: Config = Depends(get_config),
):
    await _with_config(
        config,
        FileService.upload_part,
        db=db,
        user_id=current_user.id,
        upload_id=upload_id,
        part_number=part_number,
        upload=chunk,
    )
    return ok(True)


@uploads_router.get(
    "/{upload_id}",
    summary="查询上传状态",
    response_model=ApiResponse[DiskUploadStatusOut],
    dependencies=[require_permissions(["disk:upload:status"])],
)
async def upload_status(
    upload_id: str,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
    config: Config = Depends(get_config),
):
    if not await config.upload.enable_resumable():
        raise BadRequestException(message="服务端未启用断点续传")
    data = await _with_config(
        config,
        FileService.get_upload_status,
        db=db,
        user_id=current_user.id,
        upload_id=upload_id,
    )
    return ok(DiskUploadStatusOut(**data).model_dump())


@uploads_router.post(
    "/{upload_id}/finalize",
    summary="完成分片上传",
    response_model=ApiResponse[FileEntryOut],
    dependencies=[require_permissions(["disk:upload:finalize"])],
)
async def finalize_upload(
    upload_id: str,
    data: DiskUploadFinalizeIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
    redis=Depends(get_async_redis),
    config: Config = Depends(get_config),
):
    entry = await _with_config(
        config,
        FileService.finalize_upload,
        db=db,
        redis=redis,
        user_id=current_user.id,
        upload_id=upload_id,
        parent_id=data.parent_id,
        name=data.name,
        overwrite=data.overwrite,
        mime_type=data.mime_type,
        total_parts=data.total_parts,
        commit=False,
    )
    await _with_config(
        config,
        FileService.refresh_used_space,
        db,
        current_user.id,
    )
    return ok(_to_file_entry(entry).model_dump())


@uploads_router.delete(
    "/{upload_id}",
    summary="取消上传会话",
    response_model=ApiResponse[bool],
    dependencies=[require_permissions(["disk:upload:cancel"])],
)
async def cancel_upload(
    upload_id: str,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
    redis=Depends(get_async_redis),
    config: Config = Depends(get_config),
):
    await _with_config(
        config,
        FileService.cancel_upload,
        db=db,
        redis=redis,
        user_id=current_user.id,
        upload_id=upload_id,
    )
    return ok(True)



def _to_file_entry(entry) -> FileEntryOut:
    rel_path = rel_path_from_storage(entry.user_id, entry.storage_path)
    return FileEntryOut(
        id=entry.id,
        user_id=entry.user_id,
        parent_id=entry.parent_id,
        name=entry.name,
        path=rel_path,
        is_dir=entry.is_dir,
        size=entry.size,
        mime_type=entry.mime_type,
        etag=entry.etag,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )
