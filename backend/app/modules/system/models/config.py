"""
@File: config.py
@Author: GuaiMiu
@Date: 2026/02/09
@Version: 2.0
@Description: 通用配置表模型
"""

from datetime import datetime

from sqlalchemy import Column, String, Text, Boolean, Index
from sqlmodel import Field, SQLModel


class ConfigEntry(SQLModel, table=True):
    """
    通用配置表模型。
    所有动态配置统一存储于此表。
    """

    __tablename__ = "BN_CONFIG"
    __table_args__ = (
        Index("ix_bn_config_key", "key"),
        Index("ux_bn_config_scope_key", "scope_type", "scope_id", "key", unique=True),
    )

    id: int | None = Field(default=None, primary_key=True)
    scope_type: str = Field(
        default="GLOBAL",
        sa_column=Column(String(32), nullable=False),
        description="作用域类型",
    )
    scope_id: str | None = Field(
        default=None,
        sa_column=Column(String(64), nullable=True),
        description="作用域 ID",
    )
    key: str = Field(
        sa_column=Column(String(191), nullable=False),
        description="配置键",
    )
    value: str = Field(
        default="",
        sa_column=Column(Text, nullable=False),
        description="配置值(JSON 字符串)",
    )
    value_type: str = Field(
        default="string",
        sa_column=Column(String(16), nullable=False),
        description="配置值类型",
    )
    description: str | None = Field(
        default=None,
        sa_column=Column(Text),
        description="配置说明",
    )
    is_secret: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False),
        description="是否敏感",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="创建时间",
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="更新时间",
    )
    updated_by: int | None = Field(
        default=None,
        description="更新人",
    )
