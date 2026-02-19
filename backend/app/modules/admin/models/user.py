"""
@File: auth.py
@Author: GuaiMiu
@Date: 2025/3/14 16:24
@Version: 1.0
@Description:
"""

from datetime import datetime

from pydantic import EmailStr, field_validator
from sqlalchemy import BigInteger, Column
from sqlmodel import SQLModel, Field, Relationship

from app.modules.admin.models.role import UserRoleLink
from app.enum.user import UserStatusEnum
from app.modules.system.typed.keys import ConfigKey
from app.modules.system.typed.specs import get_default
from app.utils.password import PwdUtil


def default_total_space_bytes() -> int:
    quota_gb = int(get_default(ConfigKey.AUTH_DEFAULT_USER_QUOTA_GB, 10))
    return max(quota_gb, 0) * 1024 * 1024 * 1024


class UserBase(SQLModel):

    username: str = Field(default=None, description="用户名")
    nickname: str | None = Field(default=None, description="用户昵称")
    mail: EmailStr = Field(default=None, description="用户邮箱")
    is_superuser: bool = Field(default=False, description="是否为超级管理员")
    total_space: int = Field(
        default=default_total_space_bytes(),
        sa_column=Column(BigInteger()),
        description="总空间 (单位: 字节)",
    )
    used_space: int = Field(
        default=0,
        sa_column=Column(BigInteger()),
        description="已使用空间 (单位: 字节)",
    )
    status: bool = Field(
        default=UserStatusEnum.ACTIVE.value,
        description="用户状态 0：禁用 1：启用",
    )


class User(UserBase, table=True):
    __tablename__ = "BN_SYSUSER"
    id: int = Field(default=None, primary_key=True, index=True, description="用户ID")
    password: str = Field(default=None, description="用户密码哈希")
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
    last_login_time: datetime = Field(
        default_factory=datetime.now,
        description="最后登录时间",
    )
    last_login_ip: str | None = Field(
        default=None,
        description="最后登录IP",
    )
    is_deleted: bool = Field(default=False, description="是否删除")
    roles: list["Role"] = Relationship(
        back_populates="users",
        link_model=UserRoleLink,
        sa_relationship_kwargs=dict(lazy="selectin"),
    )
    login_error_count: int = Field(default=0, description="密码错误次数")
    avatar_path: str = Field(
        default="avatar/default.jpg",
        description="用户头像 MinIO 存储路径",
    )

    @classmethod
    def create_password(cls, password):
        """
        创建密码哈希
        :param password:
        :return:
        """
        return PwdUtil.get_password_hash(password)

    def verify_password(self, input_password):
        """
        验证密码
        :param input_password: 输入的密码
        :return:
        """
        return PwdUtil.verify_password(input_password, self.password)

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, v):
        if v:
            return cls.create_password(v)
        return v

