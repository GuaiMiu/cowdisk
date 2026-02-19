"""
@File: menu.py
@Author: GuaiMiu
@Date: 2025/4/9 18:44
@Version: 1.0
@Description:
"""

from datetime import datetime

from pydantic import BaseModel

from app.modules.admin.models.menu import MenuBase


class MenuOut(MenuBase):
    """
    菜单输出模型
    """

    id: int | None = None
    create_by: str | None = None
    create_time: datetime | None = None
    update_by: str | None = None
    update_time: datetime | None = None

    # @field_serializer("create_time")
    # def create_time(self, v):
    #     return v.strftime("%Y-%m-%d %H:%M:%S")
    #
    # @field_serializer("update_time")
    # def update_time(self, v):
    #     return v.strftime("%Y-%m-%d %H:%M:%S")



class MenuRoutersOut(MenuOut):
    children: list["MenuRoutersOut"] | None = None


class MenusOut(BaseModel):
    """
    菜单列表输出模型
    """

    items: list[MenuOut]
    total: int
    page: int
    size: int
    pages: int


class MenuAddIn(MenuBase):
    """
    菜单添加输入模型
    """


class MenuEditIn(MenuBase):
    """
    菜单编辑输入模型
    """

    id: int | None = None


class MenuDeleteIn(MenuBase):
    """
    权限菜单删除输入模型
    """

    id: int | None = None


class MenusDeleteIn(BaseModel):
    """
    权限菜单批量删除输入模型
    """

    ids: list[int] | None = None

