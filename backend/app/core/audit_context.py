"""
@File: audit_context.py
@Author: GuaiMiu
@Date: 2026/02/10
@Version: 1.0
@Description: 审计上下文
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AuditContext:
    user_id: Optional[int] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None


_audit_context: ContextVar[AuditContext] = ContextVar(
    "audit_context", default=AuditContext()
)


def get_audit_context() -> AuditContext:
    return _audit_context.get()


def set_audit_context(context: AuditContext) -> None:
    _audit_context.set(context)


def clear_audit_context() -> None:
    _audit_context.set(AuditContext())
