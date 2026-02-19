"""
@File: audit.py
@Author: GuaiMiu
@Date: 2026/02/10
@Version: 1.0
@Description: 审计日志 Schema
"""

from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class AuditLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    user_id: int | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    path: str | None = None
    ip: str | None = None
    user_agent: str | None = None
    status: str
    detail: str | None = None
    created_at: datetime


class AuditLogListOut(BaseModel):
    total: int = 0
    items: list[AuditLogItem] = Field(default_factory=list)


class AuditLogQueryParams(BaseModel):
    start: datetime | None = None
    end: datetime | None = None
    user_id: int | None = None
    action: str | None = None
    status: str | None = None
    q: str | None = None
    page: int = 1
    page_size: int = 20
