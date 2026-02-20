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

from app.core.database import get_async_session
from app.core.response import ApiResponse, ok
from app.modules.admin.models.menu import Menu
from app.modules.admin.models.user import User
from app.modules.admin.schemas.menu import MenuAddIn, MenuOut, MenuEditIn, MenusDeleteIn
from app.modules.admin.services.menu import MenuService
from app.shared.deps import require_permissions, require_user

menu_router = APIRouter(
    prefix="/menus",
    tags=["Admin - Menus"],
    dependencies=[Depends(require_user)],
)


@menu_router.get(
    "",
    summary="获取权限菜单信息列表",
    response_model=ApiResponse[CursorPage[MenuOut]],
    dependencies=[require_permissions(["system:menu:list"])],
)
async def get_menu_list(
    params: CursorParams = Depends(),
    db: AsyncSession = Depends(get_async_session),
):
    query = select(Menu).where(Menu.is_deleted == False).order_by(Menu.id.asc())
    with set_page(CursorPage[MenuOut]), set_params(params), set_items_transformer(
        lambda items: [MenuOut.model_validate(item) for item in items]
    ):
        page = await paginate(db, query)
    return ok(page)


@menu_router.get(
    "/{menu_id}",
    summary="获取权限菜单信息",
    response_model=ApiResponse[MenuOut],
    dependencies=[require_permissions(["system:menu:list"])],
)
async def get_menu(
    menu_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    menu = await MenuService.get_menu(db=db, menu_id=menu_id)
    return ok(menu)


@menu_router.post(
    "",
    summary="添加权限菜单",
    response_model=ApiResponse[MenuOut],
    dependencies=[require_permissions(["system:menu:create"])],
)
async def add_menu(
    menu: MenuAddIn,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_user),
):
    db_menu = await MenuService.add_menu(db=db, menu=menu, current_user=current_user)
    return ok(db_menu, message="创建成功")


@menu_router.patch(
    "/{menu_id}",
    summary="编辑权限菜单",
    response_model=ApiResponse[MenuOut],
    dependencies=[require_permissions(["system:menu:update"])],
)
async def edit_menu(
    menu_id: int,
    menu: MenuEditIn,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_user),
):
    menu.id = menu_id
    db_menu = await MenuService.edit_menu(db=db, menu=menu, current_user=current_user)
    return ok(db_menu, message="更新成功")


@menu_router.delete(
    "/{menu_id}",
    summary="删除菜单",
    response_model=ApiResponse[MenusDeleteIn],
    dependencies=[require_permissions(["system:menu:delete"])],
)
async def delete_user(
    menu_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_user),
):
    menus = await MenuService.delete_menus(
        db=db, menus=MenusDeleteIn(ids=[menu_id]), current_user=current_user
    )
    return ok(menus, message="删除成功")


@menu_router.delete(
    "",
    summary="批量删除权限菜单",
    response_model=ApiResponse[MenusDeleteIn],
    dependencies=[require_permissions(["system:menu:delete"])],
)
async def delete_menus(
    menus: MenusDeleteIn,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_user),
):
    result = await MenuService.delete_menus(db, menus, current_user)
    return ok(result, message="删除成功")
