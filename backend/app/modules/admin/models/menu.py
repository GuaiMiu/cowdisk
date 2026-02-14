"""
@File: menu.py
@Author: GuaiMiu
@Date: 2025/3/18 21:55
@Version: 1.0
@Description:
"""

from sqlalchemy import Column, SmallInteger
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

class RoleMenuLink(SQLModel, table=True):
    __tablename__ = "BN_SYSROLE_MENU"
    role_id: int = Field(default=None, foreign_key="BN_SYSROLE.id", primary_key=True)
    menu_id: int = Field(default=None, foreign_key="BN_SYSMENU.id", primary_key=True)


class MenuBase(SQLModel):
    name: str = Field(index=True, default="菜单名")
    route_name: str | None = Field(default="路由名")
    pid: int | None = Field(default=None, index=True, description="父标识符")
    icon: str | None = Field(default=None, description="图标")
    type: int | None = Field(
        default=None,
        sa_column=Column(SmallInteger),
        description="权限类型: 1 目录, 2 菜单, 3 按钮",
    )
    permission_char: str | None = Field(default=None, description="权限字符")
    sort: int | None = Field(default=0, description="排序")
    redirect: str | None = Field(default=None, description="重定向")
    router_path: str | None = Field(default=None, description="URL路径")
    keep_alive: bool = Field(default=True, description="是否保持状态")
    component_path: str | None = Field(default=None, description="组件地址")
    status: bool = Field(default=True, description="菜单状态 1：启用 0：停用")
    is_frame: bool = Field(default=False, description="是否外连 1：是 0：否")
    description: str | None = Field(default=None, description="描述")


class Menu(MenuBase, table=True):
    __tablename__ = "BN_SYSMENU"
    id: int = Field(default=None, primary_key=True, index=True)
    is_deleted: bool = Field(default=False, description="是否删除")
    create_by: str | None = Field(
        default=None,
        description="创建者",
    )
    create_time: datetime = Field(
        default_factory=datetime.now,
        description="创建时间",
    )
    update_by: str | None = Field(
        default=None,
        description="修改者",
    )
    update_time: datetime = Field(
        default_factory=datetime.now,
        description="修改时间",
    )
    roles: list["Role"] = Relationship(
        back_populates="menus",
        link_model=RoleMenuLink,
        sa_relationship_kwargs=dict(lazy="selectin"),
    )

    def __hash__(self):
        return hash(self.id)  # 假设使用 id 作为唯一标识

    def __eq__(self, other):
        return isinstance(other, Menu) and self.id == other.id
