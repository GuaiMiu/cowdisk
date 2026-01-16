"""
@File: role.py
@Author: GuaiMiu
@Date: 2025/4/7 14:35
@Version: 1.0
@Description:
"""

from fastapi import APIRouter, Security, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.admin.models.response import ResponseModel
from app.admin.models.user import User
from app.admin.schemas.role import (
    RolesOut,
    RoleOut,
    CustomParams,
    RoleAddIn,
    RoleEditIn,
    RolesDeleteIn,
)
from app.admin.services.auth import AuthService, check_user_permission
from app.admin.services.role import RoleService
from app.core.database import get_async_session

role_router = APIRouter(
    prefix="/system/role",
    tags=["角色模块"],
    dependencies=[Depends(AuthService.get_current_user)],
)


@role_router.get(
    "/list",
    summary="获取角色列表",
    response_model=ResponseModel[RolesOut],
    dependencies=[Security(check_user_permission, scopes=["system:role:list"])],
)
async def get_role_list(
    db: AsyncSession = Depends(get_async_session),
    params: CustomParams = Depends(),
):
    """
    获取角色列表
    """
    roles = await RoleService.get_role_list(db=db, params=params)
    return ResponseModel.success(data=roles)


@role_router.get(
    "/{role_id}",
    summary="获取角色信息",
    response_model=ResponseModel[RoleOut],
    dependencies=[Security(check_user_permission, scopes=["system:role:list"])],
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
    dependencies=[Security(check_user_permission, scopes=["system:role:add"])],
)
async def add_role(
    role: RoleAddIn,
    current_user: User = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    添加角色
    """
    role = await RoleService.add_role(db=db, role=role, current_user=current_user)
    return ResponseModel.success(data=role)


@role_router.put(
    "",
    summary="编辑角色",
    response_model=ResponseModel[RoleOut],
    dependencies=[Security(check_user_permission, scopes=["system:role:edit"])],
)
async def edit_role(
    role: RoleEditIn,
    current_user: User = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    编辑角色
    """
    role = await RoleService.edit_role(db=db, role_data=role, current_user=current_user)
    return ResponseModel.success(data=role)


@role_router.delete(
    "/{role_id}",
    summary="删除角色",
    response_model=ResponseModel[int],
    dependencies=[Security(check_user_permission, scopes=["system:role:delete"])],
)
async def delete_user(
    role_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(AuthService.get_current_user),
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


@role_router.post(
    "/delete",
    summary="批量删除角色",
    response_model=ResponseModel[RolesDeleteIn],
    dependencies=[Security(check_user_permission, scopes=["system:role:delete"])],
)
async def delete_role(
    role: RolesDeleteIn,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(AuthService.get_current_user),
):
    """
    删除角色
    """
    roles = await RoleService.delete_roles(db=db, roles=role, current_user=current_user)
    return ResponseModel.success(data=roles)
