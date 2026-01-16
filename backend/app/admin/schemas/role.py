"""
@File: role.py
@Author: GuaiMiu
@Date: 2025/4/8 19:27
@Version: 1.0
@Description:
"""

from datetime import datetime

from fastapi import Query
from fastapi_pagination import Params
from pydantic import BaseModel

from app.admin.models.role import RoleBase
from app.admin.schemas.menu import MenuOut


class RoleOut(RoleBase):
    """
    角色输出模型
    """

    id: int | None = None
    name: str | None = None
    permission_char: str | None = None
    status: bool | None = None
    create_by: str | None = None
    create_time: datetime | None = None
    update_by: str | None = None
    update_time: datetime | None = None
    description: str | None = None
    menus: list["MenuOut"] | None = None

    # @field_serializer("create_time")
    # def create_time(self, v):
    #     return v.strftime("%Y-%m-%d %H:%M:%S")
    #
    # @field_serializer("update_time")
    # def update_time(self, v):
    #     return v.strftime("%Y-%m-%d %H:%M:%S")
    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }


class RolesOut(BaseModel):
    """
    角色列表输出模型
    """

    items: list[RoleOut]
    total: int
    page: int
    size: int
    pages: int


class RoleAddIn(RoleBase):
    """
    角色添加输入模型
    """

    menus: list[int] | None = None


class RoleEditIn(RoleBase):
    """
    角色编辑输入模型
    """

    id: int | None = None
    menus: list[int] | None = None


class RoleDeleteIn(RoleBase):
    """
    角色删除输入模型
    """

    id: int | None = None


class RolesDeleteIn(BaseModel):
    """
    角色批量删除输入模型
    """

    ids: list[int] | None = None


class CustomParams(Params):
    size: int = Query(50, ge=1, le=1000, description="Number of items per page")
