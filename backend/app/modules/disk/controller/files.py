"""
@File: files.py
@Author: GuaiMiu
@Date: 2026/2/7
@Version: 1.0
@Description: 文件/目录相关新接口
"""

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_session
from app.core.errors.exceptions import BadRequestException
from app.core.response import ApiResponse, ok
from app.modules.admin.models.user import User
from app.modules.disk.schemas.disk import (
    DiskTextReadOut,
    FileDeleteBatchOut,
    FileDeleteFailure,
    FileDeleteIn,
    FileEntryOut,
    FileMkdirIn,
    FileTextSaveBody,
    FileUpdateBody,
    FileUploadOut,
)
from app.modules.disk.services.file import FileService
from app.shared.deps import require_permissions, require_user

files_router = APIRouter(
    prefix="/files",
    tags=["Disk - Files"],
    dependencies=[Depends(require_user)],
)


@files_router.get(
    "",
    summary="列出目录",
    response_model=ApiResponse[dict],
    dependencies=[require_permissions(["disk:file:list"])],
)
async def list_files(
    parent_id: int | None = None,
    cursor: int = 0,
    limit: int = 200,
    order: str = "name",
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    items, total, next_cursor = await FileService.list_dir_cursor(
        db=db,
        user_id=current_user.id,
        parent_id=parent_id,
        cursor=cursor,
        limit=limit,
        order=order,
    )
    return ok(
        {
            "parent_id": parent_id,
            "items": [FileService.serialize_entry(item) for item in items],
            "total": total,
            "nextCursor": next_cursor,
        }
    )


@files_router.get(
    "/search",
    summary="按文件名搜索",
    response_model=ApiResponse[dict],
    dependencies=[require_permissions(["disk:file:list"])],
)
async def search_files(
    keyword: str,
    cursor: int = 0,
    limit: int = 200,
    order: str = "name",
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    term = (keyword or "").strip()
    if not term:
        return ok({"keyword": "", "items": [], "total": 0, "nextCursor": None})
    items, total, next_cursor = await FileService.search_by_name_cursor(
        db=db,
        user_id=current_user.id,
        keyword=term,
        cursor=cursor,
        limit=limit,
        order=order,
    )
    return ok(
        {
            "keyword": term,
            "items": [FileService.serialize_entry(item) for item in items],
            "total": total,
            "nextCursor": next_cursor,
        }
    )


@files_router.get(
    "/{file_id}",
    summary="获取文件或目录详情",
    response_model=ApiResponse[FileEntryOut],
    dependencies=[require_permissions(["disk:file:list"])],
)
async def get_file(
    file_id: int,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    entry = await FileService.get_entry(db=db, user_id=current_user.id, file_id=file_id)
    return ok(FileEntryOut.model_validate(FileService.serialize_entry(entry)).model_dump())


@files_router.post(
    "/dir",
    summary="创建目录",
    response_model=ApiResponse[FileEntryOut],
    dependencies=[require_permissions(["disk:file:mkdir"])],
)
async def create_dir(
    data: FileMkdirIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    entry = await FileService.create_dir(
        db=db,
        user_id=current_user.id,
        parent_id=data.parent_id,
        name=data.name,
    )
    return ok(FileEntryOut.model_validate(FileService.serialize_entry(entry)).model_dump(), message="创建成功")


@files_router.post(
    "/upload",
    summary="直传文件",
    response_model=ApiResponse[FileUploadOut],
    dependencies=[require_permissions(["disk:file:upload"])],
)
async def upload_file(
    files: list[UploadFile] = File(...),
    parent_id: int | None = Form(None),
    name: str | None = Form(None),
    overwrite: bool = Form(False),
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    entries = await FileService.upload_files_batch(
        db=db,
        user_id=current_user.id,
        files=files,
        parent_id=parent_id,
        name=name,
        overwrite=overwrite,
    )
    items = [FileEntryOut.model_validate(FileService.serialize_entry(entry)) for entry in entries]
    return ok(FileUploadOut(items=items).model_dump(), message="上传成功")


@files_router.patch(
    "/{file_id}",
    summary="移动或重命名文件或目录",
    response_model=ApiResponse[FileEntryOut],
    dependencies=[require_permissions(["disk:file:move"])],
)
async def update_file(
    file_id: int,
    data: FileUpdateBody,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    if data.parent_id is None and not data.name:
        raise BadRequestException(message="未提供可更新字段")
    if data.parent_id is None:
        entry = await FileService.rename(
            db=db,
            user_id=current_user.id,
            file_id=file_id,
            new_name=data.name,
        )
    else:
        entry = await FileService.move(
            db=db,
            user_id=current_user.id,
            file_id=file_id,
            target_parent_id=data.parent_id,
            new_name=data.name,
        )
    return ok(FileEntryOut.model_validate(FileService.serialize_entry(entry)).model_dump(), message="更新成功")


@files_router.delete(
    "",
    summary="删除文件或目录(进入回收站)",
    response_model=ApiResponse[FileDeleteBatchOut],
    dependencies=[require_permissions(["disk:file:delete"])],
)
async def delete_files(
    data: FileDeleteIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    result = await FileService.delete_entries_batch(
        db=db,
        user_id=current_user.id,
        file_ids=data.file_ids,
    )
    success = [int(v) for v in result.get("success", [])]
    failed = [
        FileDeleteFailure(file_id=int(item["file_id"]), error=str(item["error"]))
        for item in result.get("failed", [])
    ]
    return ok(FileDeleteBatchOut(success=success, failed=failed).model_dump())


@files_router.get(
    "/{file_id}/content",
    summary="下载或预览文件内容",
    dependencies=[require_permissions(["disk:file:download"])],
)
async def get_file_content(
    request: Request,
    file_id: int,
    disposition: str = "attachment",
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    inline = disposition == "inline"
    result = await FileService.download_direct(
        request=request,
        db=db,
        file_id=file_id,
        user_id=current_user.id,
        disposition="inline" if inline else "attachment",
        commit=False,
    )
    return result.response


@files_router.get(
    "/{file_id}/thumbnail",
    summary="获取文件缩略图",
    dependencies=[require_permissions(["disk:file:download"])],
)
async def get_file_thumbnail(
    request: Request,
    file_id: int,
    w: int = 128,
    h: int = 128,
    fit: str = "cover",
    fmt: str = "webp",
    quality: int = 82,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await FileService.build_thumbnail(
        request=request,
        db=db,
        file_id=file_id,
        user_id=current_user.id,
        width=w,
        height=h,
        fit=fit,
        fmt=fmt,
        quality=quality,
    )


@files_router.get(
    "/{file_id}/text",
    summary="读取可编辑文本",
    response_model=ApiResponse[DiskTextReadOut],
    dependencies=[require_permissions(["disk:file:edit"])],
)
async def read_text(
    file_id: int,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    data = await FileService.read_text_file(db, file_id, current_user.id)
    return ok(data)


@files_router.put(
    "/{file_id}/text",
    summary="保存可编辑文本",
    response_model=ApiResponse[FileEntryOut],
    dependencies=[require_permissions(["disk:file:edit"])],
)
async def save_text(
    file_id: int,
    data: FileTextSaveBody,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    entry = await FileService.save_text_file_with_refresh(
        db=db,
        file_id=file_id,
        content=data.content,
        user_id=current_user.id,
        overwrite=data.overwrite,
    )
    return ok(FileEntryOut.model_validate(FileService.serialize_entry(entry)).model_dump(), message="保存成功")
