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

from app.core.database import get_async_session
from app.core.response import ApiResponse, ok
from app.modules.admin.models.role import Role
from app.modules.admin.models.user import User
from app.modules.admin.schemas.role import RoleOut, RoleAddIn, RoleEditIn, RolesDeleteIn
from app.modules.admin.services.role import RoleService
from app.shared.deps import require_permissions, require_user

role_router = APIRouter(
    prefix="/roles",
    tags=["Admin - Roles"],
    dependencies=[Depends(require_user)],
)


@role_router.get(
    "",
    summary="获取角色列表",
    response_model=ApiResponse[CursorPage[RoleOut]],
    dependencies=[require_permissions(["system:role:list"])],
)
async def get_role_list(
    params: CursorParams = Depends(),
    db: AsyncSession = Depends(get_async_session),
):
    query = select(Role).where(Role.is_deleted == False).order_by(Role.id.asc())
    with set_page(CursorPage[RoleOut]), set_params(params), set_items_transformer(
        lambda items: [RoleOut.model_validate(item) for item in items]
    ):
        page = await paginate(db, query)
    return ok(page)


@role_router.get(
    "/{role_id}",
    summary="获取角色信息",
    response_model=ApiResponse[RoleOut],
    dependencies=[require_permissions(["system:role:list"])],
)
async def get_role(
    role_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    role = await RoleService.get_role(db=db, role_id=role_id)
    return ok(role)


@role_router.post(
    "",
    summary="添加角色",
    response_model=ApiResponse[RoleOut],
    dependencies=[require_permissions(["system:role:create"])],
)
async def add_role(
    role: RoleAddIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    result = await RoleService.add_role(db=db, role=role, current_user=current_user)
    return ok(result, message="创建成功")


@role_router.patch(
    "/{role_id}",
    summary="编辑角色",
    response_model=ApiResponse[RoleOut],
    dependencies=[require_permissions(["system:role:update"])],
)
async def edit_role(
    role_id: int,
    role: RoleEditIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    role.id = role_id
    result = await RoleService.edit_role(db=db, role_data=role, current_user=current_user)
    return ok(result, message="更新成功")


@role_router.delete(
    "/{role_id}",
    summary="删除角色",
    response_model=ApiResponse[RolesDeleteIn],
    dependencies=[require_permissions(["system:role:delete"])],
)
async def delete_user(
    role_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_user),
):
    roles = await RoleService.delete_roles(
        db=db, roles=RolesDeleteIn(ids=[role_id]), current_user=current_user
    )
    return ok(roles, message="删除成功")


@role_router.delete(
    "",
    summary="批量删除角色",
    response_model=ApiResponse[RolesDeleteIn],
    dependencies=[require_permissions(["system:role:delete"])],
)
async def delete_roles(
    role: RolesDeleteIn,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_user),
):
    roles = await RoleService.delete_roles(db=db, roles=role, current_user=current_user)
    return ok(roles, message="删除成功")
