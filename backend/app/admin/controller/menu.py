"""
@File: menu.py
@Author: GuaiMiu
@Date: 2025/4/13 19:45
@Version: 1.0
@Description:
"""

from fastapi import APIRouter, Depends, Security
from sqlmodel.ext.asyncio.session import AsyncSession

from app.admin.models.response import ResponseModel
from app.admin.models.user import User
from app.admin.schemas.menu import (
    MenusOut,
    MenuAddIn,
    MenuOut,
    MenuEditIn,
    MenusDeleteIn,
)
from app.admin.schemas.role import CustomParams
from app.admin.services.auth import AuthService, check_user_permission
from app.admin.services.menu import MenuService
from app.core.database import get_async_session

menu_router = APIRouter(
    prefix="/system/menu",
    tags=["菜单模块"],
    dependencies=[Depends(AuthService.get_current_user)],
)


@menu_router.get(
    "/list",
    summary="获取权限菜单信息列表",
    response_model=ResponseModel[MenusOut],
    dependencies=[Security(check_user_permission, scopes=["system:menu:list"])],
)
async def get_menu_list(
    db: AsyncSession = Depends(get_async_session),
    params: CustomParams = Depends(),
):
    """
    获取权限菜单列表
    """
    menus = await MenuService.get_menu_list(db=db, params=params)
    return ResponseModel.success(data=menus)


@menu_router.get(
    "/{menu_id}",
    summary="获取权限菜单信息",
    response_model=ResponseModel[MenuOut],
    dependencies=[Security(check_user_permission, scopes=["system:menu:list"])],
)
async def get_menu(
    menu_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """
    获取权限菜单信息
    :param menu_id:
    :param db:
    :return:
    """
    menu = await MenuService.get_menu(db=db, menu_id=menu_id)
    return ResponseModel.success(data=menu)


@menu_router.post(
    "",
    summary="添加权限菜单",
    response_model=ResponseModel[MenuOut],
    dependencies=[Security(check_user_permission, scopes=["system:menu:add"])],
)
async def add_menu(
    menu: MenuAddIn,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(AuthService.get_current_user),
):
    """
    添加权限菜单
    """
    db_menu = await MenuService.add_menu(db=db, menu=menu, current_user=current_user)
    return ResponseModel.success(data=db_menu)


@menu_router.put(
    "",
    summary="编辑权限菜单",
    response_model=ResponseModel[MenuOut],
    dependencies=[Security(check_user_permission, scopes=["system:menu:edit"])],
)
async def edit_menu(
    menu: MenuEditIn,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(AuthService.get_current_user),
):
    """
    编辑权限菜单
    """
    db_menu = await MenuService.edit_menu(db=db, menu=menu, current_user=current_user)
    return ResponseModel.success(data=db_menu)


@menu_router.delete(
    "/{menu_id}",
    summary="删除用户",
    response_model=ResponseModel[int],
    dependencies=[Security(check_user_permission, scopes=["system:menu:delete"])],
)
async def delete_user(
    menu_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(AuthService.get_current_user),
):
    """
    删除用户
    :param current_user:
    :param menu_id:
    :param db:
    :return:
    """
    menus = await MenuService.delete_menus(
        db=db, menus=MenusDeleteIn(ids=[menu_id]), current_user=current_user
    )
    return ResponseModel.success(data=menus)


@menu_router.post(
    "/delete",
    summary="批量删除权限菜单",
    response_model=ResponseModel[MenusDeleteIn],
    dependencies=[Security(check_user_permission, scopes=["system:menu:delete"])],
)
async def delete_menus(
    menus: MenusDeleteIn,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(AuthService.get_current_user),
):
    """
    批量删除权限菜单
    """
    menus = await MenuService.delete_menus(db, menus, current_user)
    return ResponseModel.success(data=menus)
