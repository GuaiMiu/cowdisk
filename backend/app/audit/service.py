"""
@File: service.py
@Author: GuaiMiu
@Date: 2026/02/10
@Version: 1.0
@Description: 审计事件构造与 outbox 写入
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable
from uuid import uuid4

from sqlmodel.ext.asyncio.session import AsyncSession

from app.audit.constants import AUDIT_OUTBOX_EVENT_TYPE, AuditOutboxStatus
from app.audit.models import AuditOutbox
from app.core.audit_context import get_audit_context
from app.modules.system.service.config import build_runtime_config


_SENSITIVE_KEYS = {
    "password",
    "passwd",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "auth",
    "secret",
    "code",
}
_SENSITIVE_PATTERN = re.compile(r"(bearer\s+)([A-Za-z0-9\-_\.=]+)", re.IGNORECASE)


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    action: str
    status: str
    resource_type: str | None
    resource_id: str | None
    path: str | None
    user_id: int | None
    ip: str | None
    user_agent: str | None
    request_id: str | None
    trace_id: str | None
    duration_ms: int | None
    detail: dict[str, Any] | None
    created_at: datetime

    def to_payload(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "action": self.action,
            "status": self.status,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "path": self.path,
            "user_id": self.user_id,
            "ip": self.ip,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "duration_ms": self.duration_ms,
            "detail": self.detail,
            "created_at": self.created_at.isoformat(),
        }


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _sanitize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, str):
        masked = _SENSITIVE_PATTERN.sub(r"\1***", value)
        return masked
    return value


def sanitize_detail(detail: dict[str, Any] | None) -> dict[str, Any] | None:
    if not detail:
        return None
    output: dict[str, Any] = {}
    for key, value in detail.items():
        lowered = str(key).lower()
        if any(marker in lowered for marker in _SENSITIVE_KEYS):
            output[key] = "***"
        else:
            output[key] = _sanitize_value(value)
    return output


def brief_error(exc: Exception | None) -> str | None:
    if not exc:
        return None
    message = str(exc)[:300]
    if not message:
        message = exc.__class__.__name__
    return _SENSITIVE_PATTERN.sub(r"\1***", message)


class AuditService:
    @classmethod
    async def build_event(
        cls,
        *,
        action: str,
        status: str,
        resource_type: str | None,
        resource_id: str | None,
        path: str | None,
        user_id: int | None,
        detail: dict[str, Any] | None,
        duration_ms: int | None,
        error: str | None,
        db: AsyncSession,
    ) -> AuditEvent | None:
        cfg = build_runtime_config(db, request_cache={})
        enabled = await cfg.audit.enable_audit()
        if not enabled:
            return None
        level = await cfg.audit.log_detail_level()
        context = get_audit_context()
        if level != "full":
            detail = None if status != "FAIL" else detail
            user_agent = None
        else:
            user_agent = context.user_agent
        if error:
            detail = detail or {}
            detail["error"] = error
        sanitized = sanitize_detail(detail)
        return AuditEvent(
            event_id=uuid4().hex,
            action=action,
            status=status,
            resource_type=resource_type,
            resource_id=resource_id,
            path=path,
            user_id=user_id or context.user_id,
            ip=context.ip,
            user_agent=user_agent,
            request_id=context.request_id,
            trace_id=context.trace_id,
            duration_ms=duration_ms,
            detail=sanitized,
            created_at=datetime.now(),
        )

    @classmethod
    async def enqueue_outbox(cls, db: AsyncSession, event: AuditEvent) -> None:
        payload = json.dumps(event.to_payload(), ensure_ascii=False)
        db.add(
            AuditOutbox(
                event_type=AUDIT_OUTBOX_EVENT_TYPE,
                payload_json=payload,
                status=AuditOutboxStatus.PENDING,
                attempts=0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )

    @staticmethod
    def merge_details(base: dict[str, Any] | None, extras: Iterable[dict[str, Any]]):
        merged = dict(base or {})
        for extra in extras:
            for key, value in extra.items():
                if value is None:
                    continue
                merged[key] = value
        return merged
