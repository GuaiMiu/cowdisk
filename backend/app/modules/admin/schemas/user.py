"""
@File: auth.py
@Author: GuaiMiu
@Date: 2025/3/18 11:27
@Version: 1.0
@Description:
"""

from datetime import datetime

from pydantic import BaseModel, field_validator

from app.modules.admin.models.user import UserBase
from app.modules.admin.schemas.role import RoleOut


class UserOut(UserBase):
    """
    用户输出模型
    """

    id: int | None = None
    create_by: str | None = None
    create_time: datetime | None = None
    update_by: str | None = None
    update_time: datetime | None = None
    last_login_ip: str | None = None
    last_login_time: datetime | None = None
    avatar_path: str | None = None
    is_superuser: bool | None = None
    roles: list["RoleOut"] | None

    @field_validator("total_space", "used_space", mode="before")
    @classmethod
    def _normalize_space(cls, value):
        if value is None:
            return 0
        return value

    # @field_serializer("create_time")
    # def create_time(self, v):
    #     return v.strftime("%Y-%m-%d %H:%M:%S")
    #
    # @field_serializer("update_time")
    # def update_time(self, v):
    #     return v.strftime("%Y-%m-%d %H:%M:%S")
    #
    # @field_serializer("last_login_time")
    # def last_login_time(self, v):
    #     return v.strftime("%Y-%m-%d %H:%M:%S")



class UsersOut(BaseModel):
    """
    用户列表输出模型
    """

    items: list[UserOut]
    total: int
    page: int
    size: int
    pages: int


class UserAddIn(UserBase):
    """
    用户添加输入模型
    """

    password: str
    roles: list[int] | None = None


class UserEditIn(UserBase):
    """
    用户编辑输入模型
    """

    id: int | None = None
    password: str | None = None
    roles: list[int] | None = None


class UserDeleteIn(UserBase):
    id: int | None = None


class UsersDeleteIn(BaseModel):
    """
    用户批量删除输入模型
    """

    ids: list[int] | None = None

