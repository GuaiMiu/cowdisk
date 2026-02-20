"""
@File: archives.py
@Author: GuaiMiu
@Date: 2026/2/7
@Version: 1.0
@Description: 压缩/解压新接口
"""

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_redis, get_async_session
from app.core.response import ApiResponse, ok
from app.modules.admin.models.user import User
from app.modules.disk.schemas.disk import DiskCompressBatchIn, DiskCompressIn, DiskExtractIn
from app.modules.disk.services.file import FileService
from app.shared.deps import require_permissions, require_user

archives_router = APIRouter(
    prefix="/archives",
    tags=["Disk - Archive"],
    dependencies=[Depends(require_user)],
)


@archives_router.post(
    "/compress",
    summary="创建压缩任务",
    response_model=ApiResponse[dict],
    dependencies=[require_permissions(["disk:archive:compress"])],
)
async def create_compress(
    data: DiskCompressIn,
    current_user: User = Depends(require_user),
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    job_id = await FileService.create_compress_job(
        db, data.file_id, current_user.id, data.name, redis
    )
    return ok({"job_id": job_id})


@archives_router.post(
    "/compress/batch",
    summary="创建批量压缩任务",
    response_model=ApiResponse[dict],
    dependencies=[require_permissions(["disk:archive:compress"])],
)
async def create_compress_batch(
    data: DiskCompressBatchIn,
    current_user: User = Depends(require_user),
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    job_id = await FileService.create_compress_batch_job(
        db, data.file_ids, current_user.id, data.name, redis
    )
    return ok({"job_id": job_id})


@archives_router.get(
    "/compress/status",
    summary="查询压缩任务状态",
    response_model=ApiResponse[dict],
    dependencies=[require_permissions(["disk:archive:status"])],
)
async def compress_status(
    job_id: str,
    current_user: User = Depends(require_user),
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    status = await FileService.get_compress_job_status(job_id, current_user.id, redis)
    await _refresh_usage_if_needed(
        status, current_user.id, f"disk:compress:{job_id}", redis, db
    )
    return ok({"status": status.get("status"), "message": status.get("message", "")})


@archives_router.post(
    "/extract",
    summary="创建解压任务",
    response_model=ApiResponse[dict],
    dependencies=[require_permissions(["disk:archive:extract"])],
)
async def create_extract(
    data: DiskExtractIn,
    current_user: User = Depends(require_user),
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    job_id = await FileService.create_extract_job(
        db, data.file_id, current_user.id, redis
    )
    return ok({"job_id": job_id})


@archives_router.get(
    "/extract/status",
    summary="查询解压任务状态",
    response_model=ApiResponse[dict],
    dependencies=[require_permissions(["disk:archive:status"])],
)
async def extract_status(
    job_id: str,
    current_user: User = Depends(require_user),
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    status = await FileService.get_extract_job_status(job_id, current_user.id, redis)
    await _refresh_usage_if_needed(
        status, current_user.id, f"disk:extract:{job_id}", redis, db
    )
    return ok({"status": status.get("status"), "message": status.get("message", "")})


async def _refresh_usage_if_needed(
    status: dict, user_id: int, job_key: str, redis, db: AsyncSession
) -> None:
    if status.get("status") == "ready" and status.get("usage_updated") != "1":
        await FileService.refresh_used_space(db, user_id)
        await redis.hset(job_key, mapping={"usage_updated": "1"})
        await redis.expire(job_key, 10800)
        status["usage_updated"] = "1"
