"""
@File: models.py
@Author: GuaiMiu
@Date: 2026/02/10
@Version: 1.0
@Description: 审计日志与 outbox 模型
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, String, Text, Index, DateTime, Integer
from sqlmodel import Field, SQLModel

from app.audit.constants import AuditOutboxStatus


class AuditLog(SQLModel, table=True):
    __tablename__ = "BN_AUDIT_LOG"
    __table_args__ = (
        Index("ix_bn_audit_log_created_at", "created_at"),
        Index("ix_bn_audit_log_user_id", "user_id"),
        Index("ix_bn_audit_log_action", "action"),
        Index("ix_bn_audit_log_status", "status"),
        Index("ux_bn_audit_log_event_id", "event_id", unique=True),
    )

    id: int | None = Field(default=None, primary_key=True)
    event_id: str = Field(sa_column=Column(String(64), nullable=False))
    user_id: int | None = Field(default=None, description="用户ID")
    action: str = Field(sa_column=Column(String(64), nullable=False))
    resource_type: str | None = Field(default=None, sa_column=Column(String(32)))
    resource_id: str | None = Field(default=None, sa_column=Column(String(64)))
    path: str | None = Field(default=None, sa_column=Column(Text))
    ip: str | None = Field(default=None, sa_column=Column(String(64)))
    user_agent: str | None = Field(default=None, sa_column=Column(Text))
    request_id: str | None = Field(default=None, sa_column=Column(String(64)))
    trace_id: str | None = Field(default=None, sa_column=Column(String(64)))
    status: str = Field(default="SUCCESS", sa_column=Column(String(16), nullable=False))
    duration_ms: int | None = Field(default=None, sa_column=Column(Integer))
    detail: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(
        default_factory=datetime.now, sa_column=Column(DateTime)
    )


class AuditOutbox(SQLModel, table=True):
    __tablename__ = "BN_AUDIT_OUTBOX"
    __table_args__ = (
        Index("ix_bn_audit_outbox_status", "status"),
        Index("ix_bn_audit_outbox_created_at", "created_at"),
        Index("ix_bn_audit_outbox_locked_at", "locked_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    event_type: str = Field(sa_column=Column(String(64), nullable=False))
    payload_json: str = Field(sa_column=Column(Text, nullable=False))
    status: str = Field(
        default=AuditOutboxStatus.PENDING, sa_column=Column(String(16), nullable=False)
    )
    attempts: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    locked_at: datetime | None = Field(default=None, sa_column=Column(DateTime))
    locked_by: str | None = Field(default=None, sa_column=Column(String(64)))
    created_at: datetime = Field(
        default_factory=datetime.now, sa_column=Column(DateTime)
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, sa_column=Column(DateTime)
    )
