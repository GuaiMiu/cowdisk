"""
@File: trash.py
@Author: GuaiMiu
@Date: 2026/2/7
@Version: 1.0
@Description: 回收站新接口
"""

from fastapi import APIRouter, Depends

from app.modules.admin.models.response import ResponseModel
from app.modules.admin.models.user import User
from app.shared.deps import require_permissions, require_user
from app.core.database import get_async_session
from app.modules.disk.schemas.disk import (
    DiskTrashBatchIdsIn,
    DiskTrashBatchOut,
    DiskTrashDeleteIn,
    DiskTrashListOut,
    DiskTrashRestoreIn,
    FileEntryOut,
)
from app.modules.disk.services.file import FileService
from sqlmodel.ext.asyncio.session import AsyncSession

trash_router = APIRouter(
    prefix="/trash",
    tags=["Disk - Trash"],
    dependencies=[Depends(require_user)],
)


@trash_router.get(
    "",
    summary="回收站列表",
    response_model=ResponseModel[DiskTrashListOut],
    dependencies=[require_permissions(["disk:trash:list"])],
)
async def list_trash(
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    获取回收站列表，仅返回顶层已删除项。
    列表由 DB 软删标记与 parent 关系推断。
    不扫描磁盘，避免与 DB 状态不一致。
    返回的 path 为逻辑路径，便于前端展示。
    幂等：同一状态下多次调用一致。
    性能：一次查询 + 逻辑路径回溯。
    权限：使用删除权限范围。
    返回：回收站条目列表。
    """
    data = await FileService.list_trash(current_user.id, db)
    return ResponseModel.success(data=data)


@trash_router.post(
    "/restore",
    summary="恢复回收站条目",
    response_model=ResponseModel[FileEntryOut],
    dependencies=[require_permissions(["disk:trash:restore"])],
)
async def restore_trash(
    data: DiskTrashRestoreIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    恢复回收站条目到原父目录。
    若出现同名冲突会自动生成新名称。
    目录恢复会联动子孙节点状态。
    物理文件会从回收站路径移回。
    并发：依赖 DB 约束检测冲突。
    成功后会刷新用户已用空间。
    错误：返回统一异常信息。
    返回：恢复后的条目。
    """
    entry = await FileService.restore_trash(int(data.id), current_user.id, db)
    await FileService.refresh_used_space(db, current_user.id)
    return ResponseModel.success(data=entry)


@trash_router.post(
    "/batch/restore",
    summary="批量恢复回收站条目",
    response_model=ResponseModel[DiskTrashBatchOut],
    dependencies=[require_permissions(["disk:trash:restore"])],
)
async def batch_restore_trash(
    data: DiskTrashBatchIdsIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    批量恢复回收站条目。
    ids 为字符串列表，内部会转换为 int。
    成功与失败数量分别统计返回。
    同名冲突会触发失败计数。
    不会因单条失败中断整体。
    成功后刷新用户已用空间。
    并发：恢复操作按序执行。
    返回：success/failed 结果。
    """
    ids = [int(value) for value in data.ids]
    result = await FileService.batch_restore_trash(ids, current_user.id, db)
    if result.get("success"):
        await FileService.refresh_used_space(db, current_user.id)
    return ResponseModel.success(data=result)


@trash_router.post(
    "/batch/delete",
    summary="批量彻底删除回收站条目",
    response_model=ResponseModel[DiskTrashBatchOut],
    dependencies=[require_permissions(["disk:trash:delete"])],
)
async def batch_delete_trash(
    data: DiskTrashBatchIdsIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    批量彻底删除回收站条目。
    删除为物理删除，无法恢复。
    会级联删除目录下所有子孙节点。
    失败条目会被收集并返回。
    不依赖磁盘遍历，使用 DB 查询。
    并发：按序执行避免资源争用。
    性能：目录越大删除越慢。
    返回：success/failed 结果。
    """
    ids = [int(value) for value in data.ids]
    result = await FileService.batch_delete_trash(ids, current_user.id, db)
    return ResponseModel.success(data=result)


@trash_router.delete(
    "",
    summary="彻底删除回收站条目",
    dependencies=[require_permissions(["disk:trash:delete"])],
)
async def delete_trash(
    data: DiskTrashDeleteIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    彻底删除单个回收站条目。
    物理删除会移除真实文件与 DB 记录。
    目录将级联删除全部子孙节点。
    若条目不存在会返回错误提示。
    并发：删除过程中不建议并行操作。
    成功后返回 True。
    性能取决于目录规模。
    返回：成功布尔值。
    """
    ok = await FileService.delete_trash(int(data.id), current_user.id, db)
    return ResponseModel.success(data=ok)


@trash_router.delete(
    "/clear",
    summary="清空回收站",
    dependencies=[require_permissions(["disk:trash:clear"])],
)
async def clear_trash(
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    清空回收站内所有条目。
    物理删除所有已删除记录与文件。
    不区分文件或目录，统一处理。
    若回收站为空返回 cleared=0。
    并发：清理过程中不建议并发恢复。
    适用于用户主动释放空间。
    性能取决于回收站大小。
    返回：清理数量。
    """
    count = await FileService.clear_trash(current_user.id, db)
    return ResponseModel.success(data={"cleared": count})



