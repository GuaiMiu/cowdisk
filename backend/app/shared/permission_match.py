from __future__ import annotations


def has_permission(user_permissions: list[str] | set[str], required: str) -> bool:
    if required in user_permissions:
        return True
    if "*:*:*" in user_permissions or "*" in user_permissions:
        return True
    parts = required.split(":")
    if not parts:
        return False
    module = parts[0]
    if f"{module}:*" in user_permissions or f"{module}:*:*" in user_permissions:
        return True
    if len(parts) >= 2:
        prefix = ":".join(parts[:2])
        if prefix in user_permissions or f"{prefix}:*" in user_permissions:
            return True
    return False
