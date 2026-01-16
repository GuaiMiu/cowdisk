"""
@File: admin_disk.py
@Author: GuaiMiu
@Date: 2025/4/5 20:26
@Version: 1.0
@Description:
"""

import mimetypes
import re
from urllib.parse import quote
from email.utils import formatdate
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, Security, UploadFile
from starlette.background import BackgroundTask
from starlette.responses import FileResponse, Response, StreamingResponse

from app.admin.models.response import ResponseModel
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
    DiskUploadOut,
    DiskEntry,
)
from app.disk.services.disk import DiskService

admin_disk_router = APIRouter(
    prefix="/disk",
    tags=["网盘管理模块"],
    dependencies=[Depends(AuthService.get_current_user_any)],
)
admin_disk_download_router = APIRouter(prefix="/disk", tags=["网盘管理模块"])


@admin_disk_router.get(
    "/list",
    summary="获取用户目录列表",
    response_model=ResponseModel[DiskListOut],
    dependencies=[Security(check_user_permission, scopes=["disk:file:list"])],
)
async def list_dir(user_id: int, path: str = ""):
    """
    获取用户目录列表
    """
    data = await DiskService.list_dir(path, user_id)
    return ResponseModel.success(data=data)


@admin_disk_router.post(
    "/mkdir",
    summary="创建用户目录",
    response_model=ResponseModel[DiskEntry],
    dependencies=[Security(check_user_permission, scopes=["disk:file:mkdir"])],
)
async def mkdir(data: DiskMkdirIn, user_id: int):
    """
    创建用户目录
    """
    entry = await DiskService.mkdir(data.path, user_id)
    return ResponseModel.success(data=entry)


@admin_disk_router.post(
    "/upload",
    summary="上传用户文件",
    response_model=ResponseModel[DiskUploadOut],
    dependencies=[Security(check_user_permission, scopes=["disk:file:upload"])],
)
async def upload_files(
    user_id: int = Form(...),
    files: list[UploadFile] = File(...),
    path: str = Form(""),
    overwrite: bool = Form(False),
    db: AsyncSession = Depends(get_async_session),
):
    """
    上传用户文件
    """
    data = await DiskService.upload(
        files=files,
        path=path,
        overwrite=overwrite,
        user_id=user_id,
        db=db,
    )
    await DiskService.refresh_used_space(user_id, db)
    return ResponseModel.success(data=data)


@admin_disk_router.post(
    "/upload/init",
    summary="分片上传初始化",
    dependencies=[Security(check_user_permission, scopes=["disk:file:upload"])],
)
async def upload_init(
    data: DiskUploadInitIn,
    user_id: int,
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    upload_id = await DiskService.init_chunk_upload(
        path=data.path,
        filename=data.filename,
        size=data.size,
        total_chunks=data.total_chunks,
        overwrite=data.overwrite,
        user_id=user_id,
        redis=redis,
        db=db,
    )
    return ResponseModel.success(data={"upload_id": upload_id})


@admin_disk_router.post(
    "/upload/chunk",
    summary="分片上传",
    dependencies=[Security(check_user_permission, scopes=["disk:file:upload"])],
)
async def upload_chunk(
    upload_id: str = Form(...),
    index: int = Form(...),
    chunk: UploadFile = File(...),
    user_id: int = Form(...),
    redis=Depends(get_async_redis),
):
    await DiskService.upload_chunk(
        upload_id=upload_id,
        index=index,
        chunk=chunk,
        user_id=user_id,
        redis=redis,
    )
    return ResponseModel.success(data=True)


@admin_disk_router.post(
    "/upload/complete",
    summary="分片上传完成",
    response_model=ResponseModel[DiskEntry],
    dependencies=[Security(check_user_permission, scopes=["disk:file:upload"])],
)
async def upload_complete(
    data: DiskUploadCompleteIn,
    user_id: int,
    redis=Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    entry = await DiskService.complete_chunk_upload(
        upload_id=data.upload_id,
        user_id=user_id,
        redis=redis,
    )
    await DiskService.refresh_used_space(user_id, db)
    return ResponseModel.success(data=entry)


@admin_disk_router.delete(
    "",
    summary="删除用户文件或目录",
    response_model=ResponseModel[DiskDeleteOut],
    dependencies=[Security(check_user_permission, scopes=["disk:file:delete"])],
)
async def delete_path(
    user_id: int,
    path: str,
    recursive: bool = False,
    db: AsyncSession = Depends(get_async_session),
):
    """
    删除用户文件或目录
    """
    data = await DiskService.delete(
        DiskDeleteIn(path=path, recursive=recursive), user_id
    )
    await DiskService.refresh_used_space(user_id, db)
    return ResponseModel.success(data=data)


@admin_disk_router.post(
    "/rename",
    summary="重命名或移动用户文件",
    response_model=ResponseModel[DiskEntry],
    dependencies=[Security(check_user_permission, scopes=["disk:file:rename"])],
)
async def rename_path(user_id: int, data: DiskRenameIn):
    """
    重命名或移动用户文件
    """
    entry = await DiskService.rename(data, user_id)
    return ResponseModel.success(data=entry)


@admin_disk_router.post(
    "/download/prepare",
    summary="打包下载准备",
    dependencies=[Security(check_user_permission, scopes=["disk:file:download"])],
)
async def prepare_download(
    data: DiskMkdirIn,
    user_id: int,
    redis=Depends(get_async_redis),
):
    job_id = await DiskService.create_download_job(data.path, user_id, redis)
    return ResponseModel.success(data={"job_id": job_id})


@admin_disk_router.post(
    "/download/token",
    summary="生成下载令牌",
    dependencies=[Security(check_user_permission, scopes=["disk:file:download"])],
)
async def create_download_token(
    data: DiskDownloadTokenIn,
    user_id: int,
    redis=Depends(get_async_redis),
):
    token = await DiskService.create_download_token(
        path=data.path,
        job_id=data.job_id,
        user_id=user_id,
        redis=redis,
    )
    return ResponseModel.success(data={"token": token})


@admin_disk_router.get(
    "/download/status",
    summary="下载任务状态",
    dependencies=[Security(check_user_permission, scopes=["disk:file:download"])],
)
async def download_status(
    job_id: str,
    user_id: int,
    redis=Depends(get_async_redis),
):
    status = await DiskService.get_download_job_status(job_id, user_id, redis)
    return ResponseModel.success(data=status)


@admin_disk_download_router.get(
    "/download",
    summary="下载用户文件",
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
    return _build_file_response(
        request=request,
        file_path=file_path,
        filename=filename,
        background=background,
    )


@admin_disk_download_router.get(
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
    return _build_file_response(
        request=request,
        file_path=file_path,
        filename=filename,
        background=BackgroundTask(_cleanup_job, file_path, job_key, redis),
    )


@admin_disk_download_router.get(
    "/preview",
    summary="预览用户文件",
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
    return _build_inline_response(
        request=request,
        file_path=file_path,
        filename=filename,
        media_type=media_type,
        background=background,
    )


def _build_file_response(
    request: Request,
    file_path: Path,
    filename: str,
    background: BackgroundTask | None,
) -> Response:
    range_header = request.headers.get("range")
    stat = file_path.stat()
    size = stat.st_size
    mtime = int(stat.st_mtime)
    last_modified = formatdate(mtime, usegmt=True)
    etag = f'W/"{size}-{mtime}"'
    if not range_header:
        return FileResponse(
            file_path,
            filename=filename,
            background=background,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(size),
                "Content-Encoding": "identity",
                "ETag": etag,
                "Last-Modified": last_modified,
            },
        )

    match = re.match(r"bytes=(\d*)-(\d*)", range_header)
    if not match:
        return Response(
            status_code=416, headers={"Content-Range": f"bytes */{size}"}
        )
    start_str, end_str = match.groups()
    start = int(start_str) if start_str else 0
    end = int(end_str) if end_str else size - 1
    if start >= size or end < start:
        return Response(
            status_code=416, headers={"Content-Range": f"bytes */{size}"}
        )

    response = StreamingResponse(
        _iter_file_range(file_path, start, end),
        status_code=206,
        headers={
            "Content-Range": f"bytes {start}-{end}/{size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "Content-Disposition": _content_disposition(filename, inline=False),
            "Content-Encoding": "identity",
            "ETag": etag,
            "Last-Modified": last_modified,

        },
        media_type="application/octet-stream",
        background=background,
    )
    return response


def _build_inline_response(
    request: Request,
    file_path: Path,
    filename: str,
    media_type: str,
    background: BackgroundTask | None,
) -> Response:
    range_header = request.headers.get("range")
    stat = file_path.stat()
    size = stat.st_size
    mtime = int(stat.st_mtime)
    last_modified = formatdate(mtime, usegmt=True)
    etag = f'W/"{size}-{mtime}"'
    if not range_header:
        return FileResponse(
            file_path,
            filename=filename,
            background=background,
            media_type=media_type,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(size),
                "Content-Encoding": "identity",
                "ETag": etag,
                "Last-Modified": last_modified,
                "Content-Disposition": _content_disposition(filename, inline=True),
            },
        )

    match = re.match(r"bytes=(\d*)-(\d*)", range_header)
    if not match:
        return Response(
            status_code=416, headers={"Content-Range": f"bytes */{size}"}
        )
    start_str, end_str = match.groups()
    start = int(start_str) if start_str else 0
    end = int(end_str) if end_str else size - 1
    if start >= size or end < start:
        return Response(
            status_code=416, headers={"Content-Range": f"bytes */{size}"}
        )

    response = StreamingResponse(
        _iter_file_range(file_path, start, end),
        status_code=206,
        headers={
            "Content-Range": f"bytes {start}-{end}/{size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "Content-Disposition": _content_disposition(filename, inline=True),
            "Content-Encoding": "identity",
            "ETag": etag,
            "Last-Modified": last_modified,
        },
        media_type=media_type,
        background=background,
    )
    return response


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
