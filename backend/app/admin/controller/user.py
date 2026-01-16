"""
@File: auth.py
@Author: GuaiMiu
@Date: 2025/3/16 00:31
@Version: 1.0
@Description:
"""

from fastapi import APIRouter, Depends, Security
from sqlmodel.ext.asyncio.session import AsyncSession

from app.admin.models.response import ResponseModel
from app.admin.models.user import User
from app.admin.schemas.role import CustomParams
from app.admin.schemas.user import (
    UsersOut,
    UserAddIn,
    UserEditIn,
    UserOut,
    UsersDeleteIn,
)
from app.admin.services.auth import AuthService, check_user_permission
from app.admin.services.user import UserService
from app.core.database import get_async_session

user_router = APIRouter(
    prefix="/system/user",
    tags=["用户模块"],
    dependencies=[Depends(AuthService.get_current_user)],
)


@user_router.get(
    "/list",
    summary="获取用户列表",
    response_model=ResponseModel[UsersOut],
    dependencies=[Security(check_user_permission, scopes=["system:user:list"])],
)
async def get_user_list(
    db: AsyncSession = Depends(get_async_session),
    params: CustomParams = Depends(),
):
    """
    获取用户列表
    """
    roles = await UserService.get_user_list(db=db, params=params)
    return ResponseModel.success(data=roles)


@user_router.get(
    "/{user_id}",
    summary="获取用户信息",
    response_model=ResponseModel[UserOut],
    dependencies=[Security(check_user_permission, scopes=["system:user:list"])],
)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """
    获取用户信息
    :param user_id:
    :param db:
    :return:
    """
    user = await UserService.get_user(db=db, user_id=user_id)
    return ResponseModel.success(data=user)


@user_router.post(
    "",
    summary="添加用户",
    response_model=ResponseModel[UserOut],
    dependencies=[Security(check_user_permission, scopes=["system:user:add"])],
)
async def add_user(
    user: UserAddIn,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(AuthService.get_current_user),
):
    """
    添加用户
    """
    role = await UserService.add_user(db=db, user=user, current_user=current_user)
    return ResponseModel.success(data=role)


@user_router.put(
    "",
    summary="编辑用户",
    response_model=ResponseModel[UserOut],
    dependencies=[Security(check_user_permission, scopes=["system:user:edit"])],
)
async def edit_user(
    user: UserEditIn,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(AuthService.get_current_user),
):
    """
    编辑用户
    """
    user = await UserService.edit_user(db=db, user=user, current_user=current_user)
    return ResponseModel.success(data=user)


@user_router.delete(
    "/{user_id}",
    summary="删除用户",
    response_model=ResponseModel[UsersDeleteIn],
    dependencies=[Security(check_user_permission, scopes=["system:user:delete"])],
)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(AuthService.get_current_user),
):
    """
    删除用户
    :param current_user:
    :param user_id:
    :param db:
    :return:
    """
    users = await UserService.delete_users(
        db=db, users=UsersDeleteIn(ids=[user_id]), current_user=current_user
    )
    return ResponseModel.success(data=users)


@user_router.post(
    "/delete",
    summary="批量删除用户",
    response_model=ResponseModel[UsersDeleteIn],
    dependencies=[Security(check_user_permission, scopes=["system:user:delete"])],
)
async def delete_users(
    users: UsersDeleteIn,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(AuthService.get_current_user),
):
    """
    批量删除用户
    """
    users = await UserService.delete_users(
        db=db, users=users, current_user=current_user
    )
    return ResponseModel.success(data=users)
