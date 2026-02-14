"""
@File: role.py
@Author: GuaiMiu
@Date: 2025/4/7 14:35
@Version: 1.0
@Description:
"""

from fastapi import APIRouter, Depends
from fastapi_pagination import set_page, set_params
from fastapi_pagination.api import set_items_transformer
from fastapi_pagination.cursor import CursorPage, CursorParams
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.admin.models.response import ResponseModel
from app.modules.admin.models.user import User
from app.modules.admin.models.role import Role
from app.modules.admin.schemas.role import RoleOut, RoleAddIn, RoleEditIn, RolesDeleteIn
from app.shared.deps import require_permissions, require_user
from app.modules.admin.services.role import RoleService
from app.core.database import get_async_session

role_router = APIRouter(
    prefix="/roles",
    tags=["Admin - Roles"],
    dependencies=[Depends(require_user)],
)


@role_router.get(
    "",
    summary="获取角色列表",
    response_model=ResponseModel[CursorPage[RoleOut]],
    dependencies=[require_permissions(["system:role:list"])],
)
async def get_role_list(
    params: CursorParams = Depends(),
    db: AsyncSession = Depends(get_async_session),
):
    """
    获取角色列表
    """
    query = select(Role).where(Role.is_deleted == False).order_by(Role.id.asc())
    with set_page(CursorPage[RoleOut]), set_params(params), set_items_transformer(
        lambda items: [RoleOut.model_validate(item) for item in items]
    ):
        page = await paginate(db, query)
    return ResponseModel.success(data=page)


@role_router.get(
    "/{role_id}",
    summary="获取角色信息",
    response_model=ResponseModel[RoleOut],
    dependencies=[require_permissions(["system:role:list"])],
)
async def get_role(
    role_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """
    获取角色信息
    :param role_id:
    :param db:
    :return:
    """
    role = await RoleService.get_role(db=db, role_id=role_id)
    return ResponseModel.success(data=role)


@role_router.post(
    "",
    summary="添加角色",
    response_model=ResponseModel[RoleOut],
    dependencies=[require_permissions(["system:role:create"])],
)
async def add_role(
    role: RoleAddIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    添加角色
    """
    role = await RoleService.add_role(db=db, role=role, current_user=current_user)
    return ResponseModel.success(data=role)


@role_router.patch(
    "/{role_id}",
    summary="编辑角色",
    response_model=ResponseModel[RoleOut],
    dependencies=[require_permissions(["system:role:update"])],
)
async def edit_role(
    role_id: int,
    role: RoleEditIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    编辑角色
    """
    role.id = role_id
    role = await RoleService.edit_role(db=db, role_data=role, current_user=current_user)
    return ResponseModel.success(data=role)


@role_router.delete(
    "/{role_id}",
    summary="删除角色",
    response_model=ResponseModel[int],
    dependencies=[require_permissions(["system:role:delete"])],
)
async def delete_user(
    role_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_user),
):
    """
    删除角色
    :param current_user:
    :param role_id:
    :param db:
    :return:
    """
    roles = await RoleService.delete_roles(
        db=db, roles=RolesDeleteIn(ids=[role_id]), current_user=current_user
    )
    return ResponseModel.success(data=roles)


@role_router.delete(
    "",
    summary="批量删除角色",
    response_model=ResponseModel[RolesDeleteIn],
    dependencies=[require_permissions(["system:role:delete"])],
)
async def delete_roles(
    role: RolesDeleteIn,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_user),
):
    """
    删除角色
    """
    roles = await RoleService.delete_roles(db=db, roles=role, current_user=current_user)
    return ResponseModel.success(data=roles)




