"""
@File: menu.py
@Author: GuaiMiu
@Date: 2025/4/13 19:43
@Version: 1.0
@Description:
"""

from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.admin.dao.menu import menu_curd
from app.modules.admin.models.menu import Menu
from app.modules.admin.models.user import User
from app.modules.admin.schemas.menu import MenuAddIn, MenuEditIn, MenusDeleteIn
from app.core.exception import ServiceException


class MenuService:
    """
    菜单服务类
    """


    @classmethod
    async def get_menu(cls, db: AsyncSession, menu_id: int):
        """
        获取权限菜单
        :param menu_id:
        :param db:
        :return:
        """
        return await menu_curd.get_by_id(db=db, obj_id=menu_id)

    @classmethod
    async def add_menu(cls, db: AsyncSession, menu: MenuAddIn, current_user: User):
        """
        添加权限菜单
        :param current_user:
        :param db:
        :param menu:
        :return:
        """
        await cls.is_menu_exist(db, menu)
        menu = Menu.model_validate(menu)
        menu.create_by = current_user.username
        db_menu = await menu_curd.create(db=db, obj=menu)
        return db_menu

    @classmethod
    async def edit_menu(cls, db: AsyncSession, menu: MenuEditIn, current_user: User):
        """
        编辑权限菜单
        :param current_user:
        :param db:
        :param menu:
        :return:
        """
        db_menu = await menu_curd.get_by_id(db=db, obj_id=menu.id)
        if not db_menu:
            raise ServiceException(
                msg=f"权限菜单 {menu.name} 不存在",
            )
        await cls.is_menu_exist(db, menu)
        menu = menu.model_dump(exclude_unset=True)
        db_menu = db_menu.sqlmodel_update(menu)
        db_menu.update_by = current_user.username
        menu = await menu_curd.update(db, db_menu)
        return menu

    @classmethod
    async def delete_menus(
        cls, db: AsyncSession, menus: MenusDeleteIn, current_user: User
    ):
        """
        批量删除角色
        :param current_user:
        :param menus:
        :param db:
        :return:
        """
        for menu_id in menus.ids:
            await menu_curd.delete(db, menu_id)
        return menus

    @classmethod
    async def is_menu_exist(cls, db: AsyncSession, menu: MenuAddIn | MenuEditIn):
        """
        判断权限菜单是否存在
        :param db:
        :param menu:
        :return:
        """
        exist = await menu_curd.get_by_or_fields(db, ["name"], menu)
        if exist:
            if exist.name == menu.name:
                raise ServiceException(
                    msg=f"菜单名称 {menu.name} 已被使用",
                )
        return False

