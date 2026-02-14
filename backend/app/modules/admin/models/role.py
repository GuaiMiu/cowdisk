"""
@File: role.py
@Author: GuaiMiu
@Date: 2025/3/17 10:43
@Version: 1.0
@Description:
"""

from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship

from app.modules.admin.models.menu import RoleMenuLink


class UserRoleLink(SQLModel, table=True):
    __tablename__ = "BN_SYSROLE_USER"
    role_id: int = Field(
        default=None,
        foreign_key="BN_SYSROLE.id",
        primary_key=True,
    )
    user_id: int = Field(
        default=None,
        foreign_key="BN_SYSUSER.id",
        primary_key=True,
    )


class RoleBase(SQLModel):
    name: str = Field(default=None, index=True)
    permission_char: str | None = Field(default=None, description="权限字符")
    status: bool = Field(default=True, description="角色状态{1:启用,0:停用}")
    description: str | None = Field(default=None, description="角色描述")


class Role(RoleBase, table=True):
    __tablename__ = "BN_SYSROLE"

    id: int = Field(default=None, primary_key=True, index=True)
    is_deleted: bool = Field(default=False, description="是否删除")
    update_time: datetime = Field(
        default_factory=datetime.now,
        description="修改时间",
    )
    update_by: str | None = Field(
        default=None,
        description="修改者",
    )
    create_by: str | None = Field(
        default=None,
        description="创建者",
    )
    create_time: datetime = Field(
        default_factory=datetime.now,
        description="创建时间",
    )
    users: list["User"] = Relationship(
        back_populates="roles",
        link_model=UserRoleLink,
        sa_relationship_kwargs=dict(lazy="selectin"),
    )
    menus: list["Menu"] = Relationship(
        back_populates="roles",
        link_model=RoleMenuLink,
        sa_relationship_kwargs=dict(lazy="selectin"),
    )

