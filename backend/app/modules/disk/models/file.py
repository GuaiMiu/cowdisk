"""
@File: file.py
@Author: GuaiMiu
@Date: 2026/2/7
@Version: 1.0
@Description: 文件索引表
"""

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Index, UniqueConstraint
from sqlmodel import Field, SQLModel


class File(SQLModel, table=True):
    __tablename__ = "BN_DISK_FILE"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "parent_id",
            "name",
            "is_deleted",
            name="uq_disk_file_user_parent_name_deleted",
        ),
        Index(
            "ix_disk_file_user_parent_deleted",
            "user_id",
            "parent_id",
            "is_deleted",
        ),
        Index(
            "ix_disk_file_storage_path",
            "storage_id",
            "storage_path_hash",
        ),
        Index(
            "ix_disk_file_user_updated",
            "user_id",
            "updated_at",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, description="用户ID")
    parent_id: int | None = Field(default=None, index=True, description="父目录ID")
    name: str = Field(description="名称")
    is_dir: bool = Field(default=False, description="是否目录")
    size: int = Field(
        default=0,
        sa_column=Column(BigInteger()),
        description="大小(字节)",
    )
    mime_type: str | None = Field(default=None, description="MIME类型")
    etag: str = Field(default="", description="ETag")
    storage_id: int = Field(index=True, description="存储ID")
    storage_path: str = Field(description="存储路径")
    storage_path_hash: str = Field(index=True, description="存储路径哈希")
    content_hash: str | None = Field(default=None, description="内容哈希")
    is_deleted: bool = Field(default=False, index=True, description="是否删除")
    deleted_at: datetime | None = Field(default=None, description="删除时间")
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime()),
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(), onupdate=datetime.now),
    )
