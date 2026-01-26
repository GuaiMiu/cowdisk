"""
@File: user.py
@Author: GuaiMiu
@Date: 2025/4/8 18:28
@Version: 1.0
@Description:
"""

from fastapi_pagination import Params
from sqlmodel.ext.asyncio.session import AsyncSession

from app.admin.dao.role import role_curd
from app.admin.dao.user import user_crud
from app.admin.models.user import User
from app.admin.schemas.user import UserAddIn, UserEditIn, UsersDeleteIn
from app.core.exception import ServiceException


class UserService:
    """
    用户服务类
    """

    @classmethod
    async def get_user_list(cls, db: AsyncSession, params: Params | None = None):
        """
        获取用户列表
        """
        if params:
            return await user_crud.get_all(db=db, params=params)
        else:
            return await user_crud.get_all(db=db)

    @classmethod
    async def get_user(cls, db: AsyncSession, user_id: int):
        """
        获取角色
        :param db:
        :param user_id:
        :return:
        """
        return await user_crud.get_by_id(db=db, obj_id=user_id)

    @classmethod
    async def add_user(cls, db: AsyncSession, user: UserAddIn, current_user: User):
        """
        添加用户
        """
        await cls.is_user_exist(db, user)
        role_ids = user.roles or []
        del user.roles
        user = User.model_validate(user)
        user.roles = await role_curd.get_all_by_ids(db=db, ids=role_ids)
        user.create_by = current_user.username
        db_user = await user_crud.create(db=db, obj=user)
        return db_user

    @classmethod
    async def edit_user(cls, db: AsyncSession, user: UserEditIn, current_user: User):
        """
        编辑用户
        """
        db_user = await user_crud.get_by_id(db=db, obj_id=user.id)
        if not db_user:
            raise ServiceException(
                msg=f"角色 {user.username} 不存在",
            )

        await cls.is_user_exist(db, user)
        if user.roles is None:
            db_user.roles = []
        else:
            db_user.roles = await role_curd.get_all_by_ids(db=db, ids=user.roles)

        payload = user.model_dump(exclude_unset=True)
        if not payload.get("password"):
            payload.pop("password", None)
        db_user = db_user.sqlmodel_update(payload)
        db_user.update_by = current_user.username
        user = await user_crud.update(db, db_user)
        return user

    @classmethod
    async def delete_users(
        cls, db: AsyncSession, users: UsersDeleteIn, current_user: User
    ):
        """
        删除用户
        :param current_user:
        :param users:
        :param db:
        :return:
        """
        for user_id in users.ids:
            await user_crud.delete(db, user_id)
        return users

    @classmethod
    async def is_user_exist(
        cls, db: AsyncSession, user: User | UserAddIn | UserEditIn
    ) -> bool:
        """
        检查用户是否存在
        :param db:
        :param user:
        :return:
        """
        exist = await user_crud.get_by_or_fields(db, ["username", "mail"], user)
        if exist:
            if exist.username == user.username and exist.mail == user.mail:
                raise ServiceException(
                    msg=f"用户名 {user.username} 邮箱 {user.mail} 已被使用",
                )
            elif exist.mail == user.mail:
                raise ServiceException(
                    msg=f"邮箱 {user.mail} 已被使用",
                )
        return False
