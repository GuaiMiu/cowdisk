"""
@File: decorator.py
@Author: GuaiMiu
@Date: 2026/02/10
@Version: 1.0
@Description: 审计装饰器
"""

from __future__ import annotations

import time
from functools import wraps
from typing import Any, Awaitable, Callable

from sqlmodel.ext.asyncio.session import AsyncSession

from app.audit.service import AuditService, brief_error

Extractor = Callable[..., Any]


def _resolve(value: str | Callable[..., str] | None, *args, **kwargs):
    if value is None:
        return None
    if callable(value):
        return value(*args, **kwargs)
    return value


def audited(
    action: str | Callable[..., str],
    resource_type: str | Callable[..., str] | None = None,
    *,
    extractors: list[Extractor] | None = None,
    auto_commit: bool = False,
):
    _ = auto_commit  # deprecated: 事务提交由业务调用方负责
    def decorator(func: Callable[..., Awaitable[Any]]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if kwargs.get("audit") is False:
                return await func(*args, **kwargs)
            request = kwargs.get("request")
            if request is not None:
                action_name = _resolve(action, *args, **kwargs, result=None, error=None)
                if (
                    action_name == "DOWNLOAD"
                    and getattr(request, "headers", None)
                    and request.headers.get("range")
                ):
                    return await func(*args, **kwargs)
            db: AsyncSession | None = kwargs.get("db") or kwargs.get("session")
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
            except Exception as exc:
                duration_ms = int((time.perf_counter() - start) * 1000)
                if db is not None:
                    extras = [
                        await _run_extractor(
                            extractor, *args, **kwargs, result=None, error=exc
                        )
                        for extractor in (extractors or [])
                    ]
                    detail = AuditService.merge_details(None, extras)
                    resource_id = detail.pop("resource_id", None) if detail else None
                    path = detail.pop("path", None) if detail else None
                    user_id = detail.pop("user_id", None) if detail else None
                    extracted_type = detail.pop("resource_type", None) if detail else None
                    resolved_type = _resolve(
                        resource_type, *args, **kwargs, result=None, error=exc
                    ) or extracted_type
                    event = await AuditService.build_event(
                        action=_resolve(action, *args, **kwargs, result=None, error=exc),
                        status="FAIL",
                        resource_type=resolved_type,
                        resource_id=resource_id,
                        path=path,
                        user_id=user_id,
                        detail=detail,
                        duration_ms=duration_ms,
                        error=brief_error(exc),
                        db=db,
                    )
                    if event:
                        await AuditService.enqueue_outbox(db, event)
                raise
            duration_ms = int((time.perf_counter() - start) * 1000)
            if db is None:
                return result
            extras = [
                await _run_extractor(
                    extractor, *args, **kwargs, result=result, error=None
                )
                for extractor in (extractors or [])
            ]
            detail = AuditService.merge_details(None, extras)
            resource_id = detail.pop("resource_id", None) if detail else None
            path = detail.pop("path", None) if detail else None
            user_id = detail.pop("user_id", None) if detail else None
            extracted_type = detail.pop("resource_type", None) if detail else None
            resolved_type = _resolve(
                resource_type, *args, **kwargs, result=result, error=None
            ) or extracted_type
            event = await AuditService.build_event(
                action=_resolve(action, *args, **kwargs, result=result, error=None),
                status="SUCCESS",
                resource_type=resolved_type,
                resource_id=resource_id,
                path=path,
                user_id=user_id,
                detail=detail,
                duration_ms=duration_ms,
                error=None,
                db=db,
            )
            if event:
                await AuditService.enqueue_outbox(db, event)
            return result

        return wrapper

    return decorator
async def _run_extractor(extractor: Extractor, *args, **kwargs) -> dict[str, Any]:
    result = extractor(*args, **kwargs)
    if isinstance(result, dict):
        return result
    if hasattr(result, "__await__"):
        awaited = await result
        return awaited if isinstance(awaited, dict) else {}
    return {}
