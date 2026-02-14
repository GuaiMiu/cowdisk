"""
@File: storage.py
@Author: GuaiMiu
@Date: 2026/2/7
@Version: 1.0
@Description: 存储配置表
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Text
from sqlmodel import Field, SQLModel


class Storage(SQLModel, table=True):
    __tablename__ = "BN_DISK_STORAGE"

    id: int | None = Field(default=None, primary_key=True)
    type: str = Field(index=True, description="local|minio")
    base_path_or_bucket: str = Field(description="基础路径或桶")
    config_text: str | None = Field(
        default="",
        sa_column=Column(Text()),
        description="通用配置文本",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime()),
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(), onupdate=datetime.now),
    )
