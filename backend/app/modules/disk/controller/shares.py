"""
@File: shares.py
@Author: GuaiMiu
@Date: 2026/2/7
@Version: 1.0
@Description: 分享管理新接口
"""

from fastapi import APIRouter, Depends
from app.modules.admin.models.response import ResponseModel
from app.modules.admin.models.user import User
from app.shared.deps import require_permissions, require_user
from app.core.database import get_async_session
from app.modules.disk.schemas.share import (
    ShareBatchIdsIn,
    ShareBatchStatusIn,
    ShareCreateIn,
    ShareListOut,
    ShareUpdateIn,
)
from app.modules.disk.services.share import ShareService
from sqlmodel.ext.asyncio.session import AsyncSession

shares_router = APIRouter(
    prefix="/shares",
    tags=["Disk - Share"],
    dependencies=[Depends(require_user)],
)


@shares_router.post(
    "",
    summary="创建分享",
    dependencies=[require_permissions(["disk:share:create"])],
)
async def create_share(
    data: ShareCreateIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    创建新的分享链接。
    仅接受 file_id 与过期、提取码参数。
    权限沿用下载权限，避免扩大权限面。
    分享状态写入数据库，便于管理与统计。
    重复创建同一文件会生成新分享记录。
    并发：同文件可同时创建多个分享。
    失败时返回统一错误消息。
    返回：分享对象结构。
    """
    share = await ShareService.create_share(
        user_id=current_user.id,
        file_id=data.fileId,
        expires_in_days=data.expiresInDays,
        expires_at=data.expiresAt,
        code=data.code,
        db=db,
    )
    return ResponseModel.success(data=share)


@shares_router.get(
    "",
    summary="分享列表",
    response_model=ResponseModel[ShareListOut],
    dependencies=[require_permissions(["disk:share:list"])],
)
async def list_shares(
    keyword: str | None = None,
    status: str | None = None,
    page: int = 1,
    size: int = 20,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    获取当前用户的分享列表。
    支持关键字与状态过滤。
    分页参数会自动约束在合理范围。
    权限沿用下载权限。
    仅查询 DB，不访问文件系统。
    幂等：相同参数返回一致结果。
    性能：分页查询避免全量。
    返回：列表与分页信息。
    """
    items, total, pages, page_size = await ShareService.list_shares(
        user_id=current_user.id,
        keyword=keyword,
        status=status,
        page=max(1, page),
        size=max(1, min(size, 100)),
        db=db,
    )
    return ResponseModel.success(
        data={
            "items": items,
            "total": total,
            "page": page,
            "size": page_size,
            "pages": pages,
        }
    )


@shares_router.post(
    "/batch/status",
    summary="批量更新分享状态",
    dependencies=[require_permissions(["disk:share:update"])],
)
async def batch_update_status(
    data: ShareBatchStatusIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    批量启用或禁用分享。
    ids 为分享 ID 列表。
    仅能操作自己创建的分享记录。
    失败条目会返回在 failed 列表中。
    幂等：重复设置同一状态不会报错。
    仅更新 DB，不涉及文件操作。
    性能：批量更新减少往返。
    返回：成功/失败统计。
    """
    result = await ShareService.batch_update_status(
        current_user.id, data.ids, data.status, db
    )
    return ResponseModel.success(data=result)


@shares_router.put(
    "/{share_id}",
    summary="更新分享",
    dependencies=[require_permissions(["disk:share:update"])],
)
async def update_share(
    share_id: str,
    data: ShareUpdateIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    更新分享配置（过期时间、提取码、状态）。
    仅能更新当前用户的分享记录。
    若 share_id 不存在将返回错误。
    权限沿用下载权限。
    并发：同一分享可被重复更新。
    只更新 DB，不影响存储内容。
    性能：单条更新。
    返回：更新后的分享对象。
    """
    share = await ShareService.update_share(
        user_id=current_user.id,
        share_id=share_id,
        expires_in_days=data.expiresInDays,
        expires_at=data.expiresAt,
        code=data.code,
        status=data.status,
        db=db,
    )
    return ResponseModel.success(data=share)


@shares_router.post(
    "/batch/delete",
    summary="批量删除分享",
    dependencies=[require_permissions(["disk:share:delete"])],
)
async def batch_delete_share(
    data: ShareBatchIdsIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    批量删除分享记录。
    删除仅影响分享链接，不影响源文件。
    失败条目会被收集返回。
    权限沿用下载权限。
    幂等：重复删除不会影响其他记录。
    仅更新 DB，不进行文件 I/O。
    性能：批量删除减少往返。
    返回：成功/失败统计。
    """
    result = await ShareService.batch_delete(current_user.id, data.ids, db)
    return ResponseModel.success(data=result)


@shares_router.delete(
    "/{share_id}",
    summary="删除分享",
    dependencies=[require_permissions(["disk:share:delete"])],
)
async def delete_share(
    share_id: str,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    删除单个分享记录。
    删除仅移除分享链接，不影响源文件。
    若记录不存在将返回错误提示。
    权限沿用下载权限。
    并发：删除操作可重复调用。
    仅更新 DB，不进行文件 I/O。
    性能：单条删除。
    返回：成功布尔值。
    """
    await ShareService.delete_share(current_user.id, share_id, db)
    return ResponseModel.success(data=True)



