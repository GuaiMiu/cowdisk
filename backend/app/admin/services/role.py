"""
@File: role.py
@Author: GuaiMiu
@Date: 2025/4/8 18:28
@Version: 1.0
@Description:
"""

from fastapi_pagination import Params
from sqlmodel.ext.asyncio.session import AsyncSession

from app.admin.dao.menu import menu_curd
from app.admin.dao.role import role_curd
from app.admin.models.role import Role
from app.admin.models.user import User
from app.admin.schemas.role import RoleAddIn, RoleEditIn, RolesDeleteIn
from app.core.exception import ServiceException


class RoleService:
    """角色服务类"""

    @classmethod
    async def get_role_list(cls, db: AsyncSession, params: Params | None = None):
        """
        获取角色列表
        :param db:
        :param params:
        :return:
        """
        if params:
            return await role_curd.get_all(db=db, params=params)
        else:
            return await role_curd.get_all(db=db)

    @classmethod
    async def get_role(cls, db: AsyncSession, role_id: int):
        """
        获取角色
        :param db:
        :param role_id:
        :return:
        """
        return await role_curd.get_by_id(db=db, obj_id=role_id)

    @classmethod
    async def add_role(cls, db: AsyncSession, role: RoleAddIn, current_user: User):
        """
        添加角色
        :param db:
        :param role:
        :param current_user:
        :return:
        """
        await cls.is_role_exist(db, role)
        menu_ids = role.menus or []
        del role.menus
        role = Role.model_validate(role)
        role.menus = await menu_curd.get_all_by_ids(db=db, ids=menu_ids)
        role.create_by = current_user.username
        db_role = await role_curd.create(db=db, obj=role)
        return db_role

    @classmethod
    async def edit_role(
        cls, db: AsyncSession, role_data: RoleEditIn, current_user: User
    ):
        """
        编辑角色
        :param current_user:
        :param db:
        :param role_data:
        :return:
        """
        db_role = await role_curd.get_by_id(db=db, obj_id=role_data.id)
        if not db_role:
            raise ServiceException(
                msg=f"角色 {role_data.name} 不存在",
            )
        await cls.is_role_exist(db, role_data)
        menu_ids = role_data.menus or []
        db_role.menus = await menu_curd.get_all_by_ids(db=db, ids=menu_ids)
        role_data = role_data.model_dump(exclude_unset=True)
        db_role = db_role.sqlmodel_update(role_data)
        db_role.update_by = current_user.username
        role = await role_curd.update(db, db_role)
        return role

    @classmethod
    async def delete_roles(
        cls, db: AsyncSession, roles: RolesDeleteIn, current_user: User
    ):
        """
        批量删除角色
        :param current_user:
        :param roles:
        :param db:
        :return:
        """
        for user_id in roles.ids:
            await role_curd.delete(db, user_id)
        return roles

    @classmethod
    async def is_role_exist(
        cls, db: AsyncSession, role: Role | RoleAddIn | RoleEditIn
    ) -> bool:
        """
        检查角色是否存在
        :param db:
        :param role:
        :return:
        """
        exist = await role_curd.get_by_or_fields(db, ["name"], role)
        if exist:
            if exist.name == role.name:
                raise ServiceException(
                    msg=f"角色名称 {role.name} 已被使用",
                )
        return False
