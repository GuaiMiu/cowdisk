"""
@File: archives.py
@Author: GuaiMiu
@Date: 2026/2/7
@Version: 1.0
@Description: 压缩/解压新接口
"""

from fastapi import APIRouter, Depends

from app.modules.admin.models.response import ResponseModel
from app.modules.admin.models.user import User
from app.shared.deps import require_permissions, require_user
from app.core.database import get_async_redis, get_async_session
from app.modules.disk.schemas.disk import DiskCompressBatchIn, DiskCompressIn, DiskExtractIn
from app.modules.disk.services.file import FileService
from sqlmodel.ext.asyncio.session import AsyncSession

archives_router = APIRouter(
    prefix="/archives",
    tags=["Disk - Archive"],
    dependencies=[Depends(require_user)],
)


@archives_router.post(
    "/compress",
    summary="创建压缩任务",
    dependencies=[require_permissions(["disk:archive:compress"])],
)
async def create_compress(
    data: DiskCompressIn,
    current_user: User = Depends(require_user),
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    """
    创建异步压缩任务，输出 ZIP 文件。
    仅接受 file_id 与可选文件名参数。
    压缩任务状态由 Redis 记录。
    任务完成后会生成新的文件条目。
    失败时会写入 error 信息供前端展示。
    并发：同一文件可重复创建任务。
    性能：大目录压缩耗时长。
    返回：job_id 标识任务。
    """
    job_id = await FileService.create_compress_job(
        db, data.file_id, current_user.id, data.name, redis
    )
    return ResponseModel.success(data={"job_id": job_id})


@archives_router.post(
    "/compress/batch",
    summary="创建批量压缩任务",
    dependencies=[require_permissions(["disk:archive:compress"])],
)
async def create_compress_batch(
    data: DiskCompressBatchIn,
    current_user: User = Depends(require_user),
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    """
    创建异步批量压缩任务，输出单个 ZIP 文件。
    file_ids 需来自同一目录，避免输出目录歧义。
    任务状态由 Redis 记录，前端可轮询 status。
    返回：job_id 标识任务。
    """
    job_id = await FileService.create_compress_batch_job(
        db, data.file_ids, current_user.id, data.name, redis
    )
    return ResponseModel.success(data={"job_id": job_id})


@archives_router.get(
    "/compress/status",
    summary="查询压缩任务状态",
    dependencies=[require_permissions(["disk:archive:status"])],
)
async def compress_status(
    job_id: str,
    current_user: User = Depends(require_user),
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    """
    查询压缩任务状态与输出路径。
    仅允许查询当前用户的任务。
    状态为 pending/ready/error。
    当任务就绪时会刷新用户已用空间。
    幂等：同一 job_id 可重复查询。
    失败时 message 返回错误信息。
    性能：单次 Redis 读取。
    返回：status 与 message。
    """
    status = await FileService.get_compress_job_status(job_id, current_user.id, redis)
    await _refresh_usage_if_needed(
        status, current_user.id, f"disk:compress:{job_id}", redis, db
    )
    return ResponseModel.success(
        data={"status": status.get("status"), "message": status.get("message", "")}
    )


@archives_router.post(
    "/extract",
    summary="创建解压任务",
    dependencies=[require_permissions(["disk:archive:extract"])],
)
async def create_extract(
    data: DiskExtractIn,
    current_user: User = Depends(require_user),
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    """
    创建异步解压任务，将 ZIP 内容解压为目录。
    仅支持 ZIP 文件，其他格式会报错。
    任务状态记录在 Redis 中。
    任务完成后会新增目录结构条目。
    失败时会写入错误信息。
    并发：同一文件可重复触发解压。
    性能：解压目录大小决定耗时。
    返回：job_id 标识任务。
    """
    job_id = await FileService.create_extract_job(
        db, data.file_id, current_user.id, redis
    )
    return ResponseModel.success(data={"job_id": job_id})


@archives_router.get(
    "/extract/status",
    summary="查询解压任务状态",
    dependencies=[require_permissions(["disk:archive:status"])],
)
async def extract_status(
    job_id: str,
    current_user: User = Depends(require_user),
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    """
    查询解压任务状态与输出路径。
    仅允许查询当前用户的任务。
    状态为 pending/ready/error。
    就绪时会刷新用户已用空间。
    幂等：同一 job_id 可重复查询。
    错误信息通过 message 返回。
    性能：单次 Redis 读取。
    返回：status 与 message。
    """
    status = await FileService.get_extract_job_status(job_id, current_user.id, redis)
    await _refresh_usage_if_needed(
        status, current_user.id, f"disk:extract:{job_id}", redis, db
    )
    return ResponseModel.success(
        data={"status": status.get("status"), "message": status.get("message", "")}
    )


async def _refresh_usage_if_needed(
    status: dict, user_id: int, job_key: str, redis, db: AsyncSession
) -> None:
    if status.get("status") == "ready" and status.get("usage_updated") != "1":
        await FileService.refresh_used_space(db, user_id)
        await redis.hset(job_key, mapping={"usage_updated": "1"})
        await redis.expire(job_key, 10800)
        status["usage_updated"] = "1"



