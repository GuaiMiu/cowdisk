"""
@File: files.py
@Author: GuaiMiu
@Date: 2026/2/7
@Version: 1.0
@Description: 文件/目录相关新接口
"""

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from app.modules.admin.models.response import ResponseModel
from app.modules.admin.models.user import User
from app.shared.deps import require_permissions, require_user
from app.core.database import get_async_session
from app.core.exception import ServiceException
from app.modules.disk.domain.paths import rel_path_from_storage
from app.modules.disk.schemas.disk import (
    DiskTextReadOut,
    FileTextSaveBody,
    FileDeleteBatchOut,
    FileDeleteFailure,
    FileDeleteIn,
    FileEntryOut,
    FileMkdirIn,
    FileUploadOut,
    FileUpdateBody,
)
from app.modules.disk.services.file import FileService
from sqlmodel.ext.asyncio.session import AsyncSession

files_router = APIRouter(
    prefix="/files",
    tags=["Disk - Files"],
    dependencies=[Depends(require_user)],
)


@files_router.get(
    "",
    summary="列出目录",
    response_model=ResponseModel[dict],
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
    """
    列出指定父目录下的子项。
    参数仅接受 parent_id 与分页信息，不再混用 path。
    权限由依赖注入保证，方法内部不再二次鉴权。
    仅查询 DB 索引，禁止任何磁盘遍历。
    若分页参数非法会抛出 ServiceException。
    结果保持旧前端使用的字段形状与顺序。
    幂等：同参数重复调用返回一致结果。
    性能：分页查询，避免一次拉取全量。
    返回：FileListOut 列表结构。
    """
    items, total, next_cursor = await FileService.list_dir_cursor(
        db=db,
        user_id=current_user.id,
        parent_id=parent_id,
        cursor=cursor,
        limit=limit,
        order=order,
    )
    return ResponseModel.success(
        data={
            "parent_id": parent_id,
            "items": [_to_file_entry(item) for item in items],
            "total": total,
            "nextCursor": next_cursor,
        }
    )


@files_router.get(
    "/{file_id}",
    summary="获取文件或目录详情",
    response_model=ResponseModel[FileEntryOut],
    dependencies=[require_permissions(["disk:file:list"])],
)
async def get_file(
    file_id: int,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    获取单个文件或目录的元信息。
    使用 file_id 作为唯一定位方式，不接受 path。
    权限依赖注入负责，函数只做业务读取。
    若文件不存在或已删除会抛出 ServiceException。
    并发安全：读取操作不会修改状态。
    性能：单条查询，避免级联读取。
    返回结构与列表条目一致，前端可复用。
    错误：透传 ServiceException 信息。
    """
    entry = await FileService.get_entry(db=db, user_id=current_user.id, file_id=file_id)
    return ResponseModel.success(data=_to_file_entry(entry))


@files_router.post(
    "/dir",
    summary="创建目录",
    response_model=ResponseModel[FileEntryOut],
    dependencies=[require_permissions(["disk:file:mkdir"])],
)
async def create_dir(
    data: FileMkdirIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    在指定 parent_id 下创建目录。
    name 会经过规范化与非法字符校验。
    若父节点不存在或不是目录将抛出错误。
    DB 唯一约束用于保证同级不重名。
    该接口仅创建目录，不涉及文件上传。
    幂等：同名已存在时返回明确错误。
    性能：单次写入与一次存储 I/O。
    返回：创建后的目录条目。
    """
    entry = await FileService.create_dir(
        db=db,
        user_id=current_user.id,
        parent_id=data.parent_id,
        name=data.name,
    )
    return ResponseModel.success(data=_to_file_entry(entry))


@files_router.post(
    "/upload",
    summary="直传文件",
    response_model=ResponseModel[FileUploadOut],
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
    """
    直传文件入口（非分片）。
    内部使用分片上传流程的单分片路径保证一致性。
    name 仅允许单文件时指定，避免歧义。
    overwrite 为 False 时遇同名会返回错误。
    上传成功后会刷新用户已用空间。
    并发：多文件会顺序处理，避免资源争用。
    权限沿用上传权限范围。
    返回：上传后的条目列表。
    """
    if name and len(files) != 1:
        raise ServiceException(msg="指定名称时仅支持单文件上传")
    items: list[FileEntryOut] = []
    for upload in files:
        entry = await FileService.upload_file(
            db=db,
            user_id=current_user.id,
            parent_id=parent_id,
            name=name,
            upload=upload,
            overwrite=overwrite,
            commit=False,
        )
        items.append(_to_file_entry(entry))
    await FileService.refresh_used_space(db, current_user.id)
    return ResponseModel.success(data=FileUploadOut(items=items))


@files_router.patch(
    "/{file_id}",
    summary="移动或重命名文件或目录",
    response_model=ResponseModel[FileEntryOut],
    dependencies=[require_permissions(["disk:file:move"])],
)
async def update_file(
    file_id: int,
    data: FileUpdateBody,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    支持更新 parent_id 与 name。
    parent_id 为空时仅重命名。
    """
    if data.parent_id is None and not data.name:
        raise ServiceException(msg="未提供可更新字段")
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
    return ResponseModel.success(data=_to_file_entry(entry))


@files_router.delete(
    "",
    summary="删除文件或目录(进入回收站)",
    response_model=ResponseModel[FileDeleteBatchOut],
    dependencies=[require_permissions(["disk:file:delete"])],
)
async def delete_files(
    data: FileDeleteIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    批量删除文件或目录，进入回收站。
    删除语义为软删，非物理删除。
    目录删除会级联其子孙记录。
    失败条目会收集错误信息返回。
    成功后刷新用户已用空间。
    幂等：已删除的条目会返回失败说明。
    性能：目录较大时可能多次递归查询。
    返回：success 与 failed 列表。
    """
    success: list[int] = []
    failed: list[FileDeleteFailure] = []
    for file_id in data.file_ids:
        try:
            entry = await FileService.delete_entry(
                db=db, user_id=current_user.id, file_id=file_id, commit=False
            )
            success.append(file_id)
        except ServiceException as exc:
            failed.append(FileDeleteFailure(file_id=file_id, error=exc.msg))
        except Exception:
            failed.append(FileDeleteFailure(file_id=file_id, error="删除失败"))
    if success:
        await FileService.refresh_used_space(db, current_user.id)
    return ResponseModel.success(
        data=FileDeleteBatchOut(success=success, failed=failed)
    )


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
    "/{file_id}/text",
    summary="读取可编辑文本",
    response_model=ResponseModel[DiskTextReadOut],
    dependencies=[require_permissions(["disk:file:edit"])],
)
async def read_text(
    file_id: int,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    读取文本类文件内容用于在线编辑。
    仅支持文本文件，二进制会报错或截断。
    权限沿用下载权限，避免重复校验逻辑。
    不会改变文件元信息或内容。
    出错时使用统一异常响应格式。
    幂等：重复调用返回相同内容。
    性能：单文件读取，大小过大可能慢。
    返回：文本内容与大小信息。
    """
    data = await FileService.read_text_file(db, file_id, current_user.id)
    return ResponseModel.success(data=data)


@files_router.put(
    "/{file_id}/text",
    summary="保存可编辑文本",
    response_model=ResponseModel[FileEntryOut],
    dependencies=[require_permissions(["disk:file:edit"])],
)
async def save_text(
    file_id: int,
    data: FileTextSaveBody,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    保存文本文件内容。
    file_id 从路径中获取，避免 body 与 path 混用。
    支持 overwrite 语义，用于冲突控制。
    写入后更新文件元信息与 etag。
    权限沿用上传权限，避免绕过写入限制。
    并发：依赖服务层的存储原子写入。
    性能：直接写文本，不走分片上传。
    返回：更新后的文件条目。
    """
    entry = await FileService.save_text_file(
        db, file_id, data.content, current_user.id, data.overwrite
    )
    return ResponseModel.success(data=_to_file_entry(entry))


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




