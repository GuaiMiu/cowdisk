"""
@File: deps.py
@Author: GuaiMiu
@Date: 2026/02/10
@Version: 1.0
@Description: 统一依赖注入封装
"""

from fastapi import Depends, Security

from app.modules.admin.models.user import User
from app.core.audit_context import AuditContext, get_audit_context, set_audit_context
from app.modules.admin.services.auth import AuthService, check_user_permission


async def require_user(
    current_user: User = Depends(AuthService.get_current_user),
) -> User:
    current = get_audit_context()
    set_audit_context(
        AuditContext(
            user_id=current_user.id,
            ip=current.ip,
            user_agent=current.user_agent,
            request_id=current.request_id,
            trace_id=current.trace_id,
        )
    )
    return current_user


def require_permissions(scopes: list[str]):
    return Security(check_user_permission, scopes=scopes)

