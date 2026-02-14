"""
@File: share.py
@Author: GuaiMiu
@Date: 2025/4/5 20:26
@Version: 1.0
@Description: 分享表
"""

from datetime import datetime
from uuid import uuid4

from sqlmodel import SQLModel, Field


class Share(SQLModel, table=True):
    __tablename__ = "BN_DISK_SHARE"

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True, index=True)
    user_id: int = Field(index=True, description="创建者ID")
    token: str = Field(default_factory=lambda: uuid4().hex, index=True)
    file_id: int = Field(index=True, description="分享文件ID")
    resource_type: str = Field(description="FILE|FOLDER")
    path: str = Field(default="", description="分享路径(相对用户根目录)")
    name: str = Field(description="分享名称")
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime | None = Field(default=None)
    code: str | None = Field(default=None)
    status: int = Field(default=1, description="0 cancelled, 1 active")
    is_deleted: bool = Field(default=False, description="是否删除")
