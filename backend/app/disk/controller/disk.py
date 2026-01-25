"""
@File: disk.py
@Author: GuaiMiu
@Date: 2025/4/5 20:26
@Version: 1.0
@Description:
"""

import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, Security, UploadFile
from starlette.background import BackgroundTask

from app.admin.models.response import ResponseModel
from app.admin.models.user import User
from app.admin.services.auth import AuthService, check_user_permission
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_redis, get_async_session
from app.core.exception import ServiceException
from app.disk.schemas.disk import (
    DiskDeleteIn,
    DiskDeleteOut,
    DiskListOut,
    DiskDownloadTokenIn,
    DiskUploadCompleteIn,
    DiskUploadInitIn,
    DiskMkdirIn,
    DiskRenameIn,
    DiskCompressIn,
    DiskExtractIn,
    DiskTextReadOut,
    DiskTextSaveIn,
    DiskUploadOut,
    DiskEntry,
    DiskTrashListOut,
    DiskTrashRestoreIn,
    DiskTrashDeleteIn,
)
from app.disk.services.disk import DiskService
from app.disk.utils.streaming import build_file_response, build_inline_response

disk_router = APIRouter(
    prefix="/disk",
    tags=["网盘模块"],
    dependencies=[Depends(AuthService.get_current_user_any)],
)
disk_download_router = APIRouter(prefix="/disk", tags=["网盘模块"])


@disk_router.get(
    "/list",
    summary="获取目录列表",
    response_model=ResponseModel[DiskListOut],
    dependencies=[Security(check_user_permission, scopes=["disk:file:list"])],
)
async def list_dir(
    path: str = "",
    current_user: User = Depends(AuthService.get_current_user_any),
):
    """
    获取目录列表
    """
    data = await DiskService.list_dir(path, current_user.id)
    return ResponseModel.success(data=data)


@disk_router.post(
    "/mkdir",
    summary="创建目录",
    response_model=ResponseModel[DiskEntry],
    dependencies=[Security(check_user_permission, scopes=["disk:file:mkdir"])],
)
async def mkdir(
    data: DiskMkdirIn,
    current_user: User = Depends(AuthService.get_current_user_any),
):
    """
    创建目录
    """
    entry = await DiskService.mkdir(data.path, current_user.id)
    return ResponseModel.success(data=entry)


@disk_router.post(
    "/upload",
    summary="上传文件",
    response_model=ResponseModel[DiskUploadOut],
    dependencies=[Security(check_user_permission, scopes=["disk:file:upload"])],
)
async def upload_files(
    files: list[UploadFile] = File(...),
    path: str = Form(""),
    overwrite: bool = Form(False),
    current_user: User = Depends(AuthService.get_current_user_any),
    db: AsyncSession = Depends(get_async_session),
):
    """
    上传文件
    """
    data = await DiskService.upload(
        files=files,
        path=path,
        overwrite=overwrite,
        user_id=current_user.id,
        db=db,
    )
    await DiskService.refresh_used_space(current_user.id, db)
    return ResponseModel.success(data=data)


@disk_router.post(
    "/upload/init",
    summary="分片上传初始化",
    dependencies=[Security(check_user_permission, scopes=["disk:file:upload"])],
)
async def upload_init(
    data: DiskUploadInitIn,
    current_user: User = Depends(AuthService.get_current_user_any),
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    upload_id = await DiskService.init_chunk_upload(
        path=data.path,
        filename=data.filename,
        size=data.size,
        total_chunks=data.total_chunks,
        overwrite=data.overwrite,
        user_id=current_user.id,
        redis=redis,
        db=db,
    )
    return ResponseModel.success(data={"upload_id": upload_id})


@disk_router.post(
    "/upload/chunk",
    summary="分片上传",
    dependencies=[Security(check_user_permission, scopes=["disk:file:upload"])],
)
async def upload_chunk(
    upload_id: str = Form(...),
    index: int = Form(...),
    chunk: UploadFile = File(...),
    current_user: User = Depends(AuthService.get_current_user_any),
    redis=Depends(get_async_redis),
):
    await DiskService.upload_chunk(
        upload_id=upload_id,
        index=index,
        chunk=chunk,
        user_id=current_user.id,
        redis=redis,
    )
    return ResponseModel.success(data=True)


@disk_router.post(
    "/upload/complete",
    summary="分片上传完成",
    response_model=ResponseModel[DiskEntry],
    dependencies=[Security(check_user_permission, scopes=["disk:file:upload"])],
)
async def upload_complete(
    data: DiskUploadCompleteIn,
    current_user: User = Depends(AuthService.get_current_user_any),
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    entry = await DiskService.complete_chunk_upload(
        upload_id=data.upload_id,
        user_id=current_user.id,
        redis=redis,
    )
    await DiskService.refresh_used_space(current_user.id, db)
    return ResponseModel.success(data=entry)


@disk_router.delete(
    "",
    summary="删除文件或目录",
    response_model=ResponseModel[DiskDeleteOut],
    dependencies=[Security(check_user_permission, scopes=["disk:file:delete"])],
)
async def delete_path(
    path: str,
    recursive: bool = False,
    current_user: User = Depends(AuthService.get_current_user_any),
    db: AsyncSession = Depends(get_async_session),
):
    """
    删除文件或目录
    """
    data = await DiskService.delete(
        DiskDeleteIn(path=path, recursive=recursive),
        current_user.id,
    )
    await DiskService.refresh_used_space(current_user.id, db)
    return ResponseModel.success(data=data)


@disk_router.post(
    "/rename",
    summary="重命名或移动文件",
    response_model=ResponseModel[DiskEntry],
    dependencies=[Security(check_user_permission, scopes=["disk:file:rename"])],
)
async def rename_path(
    data: DiskRenameIn,
    current_user: User = Depends(AuthService.get_current_user_any),
):
    """
    重命名或移动文件
    """
    entry = await DiskService.rename(data, current_user.id)
    return ResponseModel.success(data=entry)


@disk_router.get(
    "/edit",
    summary="读取可编辑文本",
    response_model=ResponseModel[DiskTextReadOut],
    dependencies=[Security(check_user_permission, scopes=["disk:file:download"])],
)
async def read_text_file(
    path: str,
    current_user: User = Depends(AuthService.get_current_user_any),
):
    data = await DiskService.read_text_file(path, current_user.id)
    return ResponseModel.success(data=data)


@disk_router.post(
    "/edit",
    summary="保存可编辑文本",
    response_model=ResponseModel[DiskEntry],
    dependencies=[Security(check_user_permission, scopes=["disk:file:upload"])],
)
async def save_text_file(
    data: DiskTextSaveIn,
    current_user: User = Depends(AuthService.get_current_user_any),
):
    entry = await DiskService.save_text_file(data.path, data.content, current_user.id)
    return ResponseModel.success(data=entry)


@disk_router.post(
    "/download/prepare",
    summary="打包下载准备",
    dependencies=[Security(check_user_permission, scopes=["disk:file:download"])],
)
async def prepare_download(
    data: DiskMkdirIn,
    current_user: User = Depends(AuthService.get_current_user_any),
    redis=Depends(get_async_redis),
):
    job_id = await DiskService.create_download_job(data.path, current_user.id, redis)
    return ResponseModel.success(data={"job_id": job_id})


@disk_router.post(
    "/compress/prepare",
    summary="压缩任务创建",
    dependencies=[Security(check_user_permission, scopes=["disk:file:upload"])],
)
async def prepare_compress(
    data: DiskCompressIn,
    current_user: User = Depends(AuthService.get_current_user_any),
    redis=Depends(get_async_redis),
):
    job_id = await DiskService.create_compress_job(
        data.path, current_user.id, data.name, redis
    )
    return ResponseModel.success(data={"job_id": job_id})


@disk_router.get(
    "/compress/status",
    summary="压缩任务状态",
    dependencies=[Security(check_user_permission, scopes=["disk:file:upload"])],
)
async def compress_status(
    job_id: str,
    current_user: User = Depends(AuthService.get_current_user_any),
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    status = await DiskService.get_compress_job_status(job_id, current_user.id, redis)
    await _refresh_usage_if_needed(
        status, current_user.id, f"disk:compress:{job_id}", redis, db
    )
    return ResponseModel.success(
        data={"status": status.get("status"), "message": status.get("message", "")}
    )


@disk_router.post(
    "/extract/prepare",
    summary="解压任务创建",
    dependencies=[Security(check_user_permission, scopes=["disk:file:upload"])],
)
async def prepare_extract(
    data: DiskExtractIn,
    current_user: User = Depends(AuthService.get_current_user_any),
    redis=Depends(get_async_redis),
):
    job_id = await DiskService.create_extract_job(data.path, current_user.id, redis)
    return ResponseModel.success(data={"job_id": job_id})


@disk_router.get(
    "/extract/status",
    summary="解压任务状态",
    dependencies=[Security(check_user_permission, scopes=["disk:file:upload"])],
)
async def extract_status(
    job_id: str,
    current_user: User = Depends(AuthService.get_current_user_any),
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    status = await DiskService.get_extract_job_status(job_id, current_user.id, redis)
    await _refresh_usage_if_needed(
        status, current_user.id, f"disk:extract:{job_id}", redis, db
    )
    return ResponseModel.success(
        data={"status": status.get("status"), "message": status.get("message", "")}
    )


@disk_router.get(
    "/trash",
    summary="回收站列表",
    response_model=ResponseModel[DiskTrashListOut],
    dependencies=[Security(check_user_permission, scopes=["disk:file:delete"])],
)
async def list_trash(
    current_user: User = Depends(AuthService.get_current_user_any),
):
    data = await DiskService.list_trash(current_user.id)
    return ResponseModel.success(data=data)


@disk_router.post(
    "/trash/restore",
    summary="回收站恢复",
    response_model=ResponseModel[DiskEntry],
    dependencies=[Security(check_user_permission, scopes=["disk:file:delete"])],
)
async def restore_trash(
    data: DiskTrashRestoreIn,
    current_user: User = Depends(AuthService.get_current_user_any),
    db: AsyncSession = Depends(get_async_session),
):
    entry = await DiskService.restore_trash(data.id, current_user.id)
    await DiskService.refresh_used_space(current_user.id, db)
    return ResponseModel.success(data=entry)


@disk_router.delete(
    "/trash",
    summary="回收站删除",
    dependencies=[Security(check_user_permission, scopes=["disk:file:delete"])],
)
async def delete_trash(
    data: DiskTrashDeleteIn,
    current_user: User = Depends(AuthService.get_current_user_any),
):
    ok = await DiskService.delete_trash(data.id, current_user.id)
    return ResponseModel.success(data=ok)


@disk_router.delete(
    "/trash/clear",
    summary="清空回收站",
    dependencies=[Security(check_user_permission, scopes=["disk:file:delete"])],
)
async def clear_trash(
    current_user: User = Depends(AuthService.get_current_user_any),
):
    count = await DiskService.clear_trash(current_user.id)
    return ResponseModel.success(data={"cleared": count})


@disk_router.post(
    "/download/token",
    summary="生成下载令牌",
    dependencies=[Security(check_user_permission, scopes=["disk:file:download"])],
)
async def create_download_token(
    data: DiskDownloadTokenIn,
    current_user: User = Depends(AuthService.get_current_user_any),
    redis=Depends(get_async_redis),
):
    token = await DiskService.create_download_token(
        path=data.path,
        job_id=data.job_id,
        user_id=current_user.id,
        redis=redis,
    )
    return ResponseModel.success(data={"token": token})


@disk_router.get(
    "/download/status",
    summary="下载任务状态",
    dependencies=[Security(check_user_permission, scopes=["disk:file:download"])],
)
async def download_status(
    job_id: str,
    current_user: User = Depends(AuthService.get_current_user_any),
    redis=Depends(get_async_redis),
):
    status = await DiskService.get_download_job_status(job_id, current_user.id, redis)
    return ResponseModel.success(data=status)


@disk_download_router.get(
    "/download",
    summary="下载文件",
)
async def download_token_file(
    request: Request,
    token: str,
    redis=Depends(get_async_redis),
):
    info = await DiskService.get_download_token(token, redis)
    if info.get("type") != "file":
        raise ServiceException(msg="下载令牌类型错误")
    user_id = int(info.get("user_id", "0"))
    if not user_id:
        raise ServiceException(msg="下载令牌无效")
    file_path, filename, cleanup = await DiskService.prepare_download(
        info.get("path", ""), user_id
    )
    background = BackgroundTask(_cleanup_file, file_path) if cleanup else None
    return build_file_response(
        request=request,
        file_path=file_path,
        filename=filename,
        background=background,
    )


@disk_download_router.get(
    "/download/job",
    summary="下载任务文件",
)
async def download_token_job(
    request: Request,
    token: str,
    redis=Depends(get_async_redis),
):
    info = await DiskService.get_download_token(token, redis)
    if info.get("type") != "job":
        raise ServiceException(msg="下载令牌类型错误")
    user_id = int(info.get("user_id", "0"))
    if not user_id:
        raise ServiceException(msg="下载令牌无效")
    file_path, filename = await DiskService.get_download_job_file(
        info.get("job_id", ""), user_id, redis
    )
    job_key = f"disk:download:{info.get('job_id', '')}"
    return build_file_response(
        request=request,
        file_path=file_path,
        filename=filename,
        background=BackgroundTask(_cleanup_job, file_path, job_key, redis),
    )


@disk_download_router.api_route(
    "/preview",
    methods=["GET", "HEAD"],
    summary="预览文件",
)
async def preview_file(
    request: Request,
    token: str,
    redis=Depends(get_async_redis),
):
    info = await DiskService.get_download_token(token, redis)
    if info.get("type") != "file":
        raise ServiceException(msg="下载令牌类型错误")
    user_id = int(info.get("user_id", "0"))
    if not user_id:
        raise ServiceException(msg="下载令牌无效")
    file_path, filename, cleanup = await DiskService.prepare_download(
        info.get("path", ""), user_id
    )
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    background = BackgroundTask(_cleanup_file, file_path) if cleanup else None
    return build_inline_response(
        request=request,
        file_path=file_path,
        filename=filename,
        media_type=media_type,
        background=background,
    )


def _cleanup_file(file_path: Path):
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        return


async def _cleanup_job(file_path: Path, job_key: str, redis):
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        pass
    if job_key:
        try:
            await redis.delete(job_key)
        except Exception:
            return


async def _refresh_usage_if_needed(
    status: dict, user_id: int, job_key: str, redis, db: AsyncSession
) -> None:
    if status.get("status") == "ready" and status.get("usage_updated") != "1":
        await DiskService.refresh_used_space(user_id, db)
        await redis.hset(job_key, mapping={"usage_updated": "1"})
        await redis.expire(job_key, 10800)
        status["usage_updated"] = "1"
