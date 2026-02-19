"""
@File: middleware.py
@Author: GuaiMiu
@Date: 2026/02/10
@Version: 1.0
@Description: 审计上下文中间件
"""

from __future__ import annotations

from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

from app.core.audit_context import AuditContext, clear_audit_context, set_audit_context


def _extract_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


class AuditContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid4().hex
        trace_id = request.headers.get("x-trace-id")
        context = AuditContext(
            user_id=None,
            ip=_extract_ip(request),
            user_agent=request.headers.get("user-agent"),
            request_id=request_id,
            trace_id=trace_id,
        )
        set_audit_context(context)
        try:
            response = await call_next(request)
            response.headers.setdefault("x-request-id", request_id)
            return response
        finally:
            clear_audit_context()
