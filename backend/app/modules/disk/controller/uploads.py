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

from app.modules.admin.models.response import ResponseModel
from app.modules.admin.models.user import User
from app.core.database import get_async_session
from app.core.exception import ServiceException
from app.shared.deps import require_permissions, require_user
from app.modules.disk.schemas.disk import (
    DiskUploadFinalizeIn,
    DiskUploadInitIn,
    DiskUploadInitOut,
    DiskUploadStatusOut,
    FileEntryOut,
)
from app.modules.disk.domain.paths import rel_path_from_storage
from app.modules.disk.services.file import FileService
from app.modules.system.deps import get_config
from app.modules.system.typed.config import Config

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
    response_model=ResponseModel[DiskUploadInitOut],
    dependencies=[require_permissions(["disk:upload:init"])],
)
async def init_upload(
    data: DiskUploadInitIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
    config: Config = Depends(get_config),
):
    """
    初始化分片上传会话并返回 upload_id。
    会话状态完全由文件系统目录表达。
    不会在数据库创建上传记录，避免状态分裂。
    同名冲突与父目录校验由服务层完成。
    part_size 与 total_parts 会在返回中固定。
    幂等：同参数重复调用会生成新会话。
    性能：仅创建少量目录，开销可控。
    返回：upload_id 与过期时间信息。
    """
    result = await _with_config(
        config,
        FileService.init_upload_session,
        db=db,
        user_id=current_user.id,
        parent_id=data.parent_id,
        name=data.name,
        size=data.size,
        part_size=data.part_size,
        overwrite=data.overwrite,
    )
    upload_config = await _build_upload_policy(config)
    return ResponseModel.success(
        data=DiskUploadInitOut(**result, upload_config=upload_config)
    )


@uploads_router.get(
    "/policy",
    summary="获取上传策略",
    response_model=ResponseModel[dict],
    dependencies=[require_permissions(["disk:upload:init"])],
)
async def get_upload_policy(config: Config = Depends(get_config)):
    data = await _build_upload_policy(config)
    return ResponseModel.success(data=data)


@uploads_router.put(
    "/{upload_id}/parts/{part_number}",
    summary="上传分片",
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
    """
    上传指定序号分片，支持幂等重试。
    分片文件名固定 8 位宽度，避免排序问题。
    存储后端使用写临时文件后原子替换。
    若分片已存在但大小不一致则报冲突。
    每次成功写入会更新会话目录 mtime。
    并发：不同分片可并行上传。
    错误：透传 ServiceException 原因。
    返回：成功布尔值。
    """
    await _with_config(
        config,
        FileService.upload_part,
        db=db,
        user_id=current_user.id,
        upload_id=upload_id,
        part_number=part_number,
        upload=chunk,
    )
    return ResponseModel.success(data=True)


@uploads_router.get(
    "/{upload_id}",
    summary="查询上传状态",
    response_model=ResponseModel[DiskUploadStatusOut],
    dependencies=[require_permissions(["disk:upload:status"])],
)
async def upload_status(
    upload_id: str,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
    config: Config = Depends(get_config),
):
    """
    查询上传会话状态与已上传分片。
    状态由目录/文件事实推断，不读取数据库。
    会话不存在时返回明确错误提示。
    结果包含 missing_parts 便于前端补传。
    expires_in 基于目录 mtime 与 TTL 计算。
    并发安全：只读操作不修改状态。
    性能：扫描一次 parts 目录。
    返回：状态结构体。
    """
    if not await config.upload.enable_resumable():
        raise ServiceException(msg="服务端未启用断点续传")
    data = await _with_config(
        config,
        FileService.get_upload_status,
        db=db,
        user_id=current_user.id,
        upload_id=upload_id,
    )
    return ResponseModel.success(data=DiskUploadStatusOut(**data))


@uploads_router.post(
    "/{upload_id}/finalize",
    summary="完成分片上传",
    response_model=ResponseModel[FileEntryOut],
    dependencies=[require_permissions(["disk:upload:finalize"])],
)
async def finalize_upload(
    upload_id: str,
    data: DiskUploadFinalizeIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
    config: Config = Depends(get_config),
):
    """
    合并分片并写入最终文件。
    通过 .lock 文件保证 finalize 并发安全。
    若 .done 已存在则返回幂等成功。
    合并完成后更新 DB 元数据与存储路径。
    若合并失败会清理临时文件并回滚。
    总分片数可由 upload_id 推断或显式传入。
    性能：按序读取分片，内存占用恒定。
    返回：最终文件条目。
    """
    entry = await _with_config(
        config,
        FileService.finalize_upload,
        db=db,
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
    return ResponseModel.success(data=_to_file_entry(entry))


@uploads_router.delete(
    "/{upload_id}",
    summary="取消上传会话",
    dependencies=[require_permissions(["disk:upload:cancel"])],
)
async def cancel_upload(
    upload_id: str,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
    config: Config = Depends(get_config),
):
    """
    取消上传会话并删除临时目录。
    若会话正在 finalize（存在 .lock）将报冲突。
    不触碰数据库记录，避免误删正式文件。
    幂等：会话不存在也返回成功。
    适用于用户主动取消或重置失败上传。
    会话目录删除后不可恢复。
    性能：删除单个会话目录。
    返回：成功布尔值。
    """
    await _with_config(
        config,
        FileService.cancel_upload,
        db=db,
        user_id=current_user.id,
        upload_id=upload_id,
    )
    return ResponseModel.success(data=True)


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



