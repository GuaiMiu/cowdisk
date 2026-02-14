"""
@File: menu.py
@Author: GuaiMiu
@Date: 2025/4/13 19:45
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
from app.modules.admin.models.menu import Menu
from app.modules.admin.schemas.menu import MenuAddIn, MenuOut, MenuEditIn, MenusDeleteIn
from app.shared.deps import require_permissions, require_user
from app.modules.admin.services.menu import MenuService
from app.core.database import get_async_session

menu_router = APIRouter(
    prefix="/menus",
    tags=["Admin - Menus"],
    dependencies=[Depends(require_user)],
)


@menu_router.get(
    "",
    summary="获取权限菜单信息列表",
    response_model=ResponseModel[CursorPage[MenuOut]],
    dependencies=[require_permissions(["system:menu:list"])],
)
async def get_menu_list(
    params: CursorParams = Depends(),
    db: AsyncSession = Depends(get_async_session),
):
    """
    获取权限菜单列表
    """
    query = select(Menu).where(Menu.is_deleted == False).order_by(Menu.id.asc())
    with set_page(CursorPage[MenuOut]), set_params(params), set_items_transformer(
        lambda items: [MenuOut.model_validate(item) for item in items]
    ):
        page = await paginate(db, query)
    return ResponseModel.success(data=page)


@menu_router.get(
    "/{menu_id}",
    summary="获取权限菜单信息",
    response_model=ResponseModel[MenuOut],
    dependencies=[require_permissions(["system:menu:list"])],
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
    dependencies=[require_permissions(["system:menu:create"])],
)
async def add_menu(
    menu: MenuAddIn,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_user),
):
    """
    添加权限菜单
    """
    db_menu = await MenuService.add_menu(db=db, menu=menu, current_user=current_user)
    return ResponseModel.success(data=db_menu)


@menu_router.patch(
    "/{menu_id}",
    summary="编辑权限菜单",
    response_model=ResponseModel[MenuOut],
    dependencies=[require_permissions(["system:menu:update"])],
)
async def edit_menu(
    menu_id: int,
    menu: MenuEditIn,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_user),
):
    """
    编辑权限菜单
    """
    menu.id = menu_id
    db_menu = await MenuService.edit_menu(db=db, menu=menu, current_user=current_user)
    return ResponseModel.success(data=db_menu)


@menu_router.delete(
    "/{menu_id}",
    summary="删除菜单",
    response_model=ResponseModel[int],
    dependencies=[require_permissions(["system:menu:delete"])],
)
async def delete_user(
    menu_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_user),
):
    """
    删除菜单
    :param current_user:
    :param menu_id:
    :param db:
    :return:
    """
    menus = await MenuService.delete_menus(
        db=db, menus=MenusDeleteIn(ids=[menu_id]), current_user=current_user
    )
    return ResponseModel.success(data=menus)


@menu_router.delete(
    "",
    summary="批量删除权限菜单",
    response_model=ResponseModel[MenusDeleteIn],
    dependencies=[require_permissions(["system:menu:delete"])],
)
async def delete_menus(
    menus: MenusDeleteIn,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_user),
):
    """
    批量删除权限菜单
    """
    menus = await MenuService.delete_menus(db, menus, current_user)
    return ResponseModel.success(data=menus)




