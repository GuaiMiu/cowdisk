from __future__ import annotations

from app.modules.system.typed.specs import REGISTRY


GROUP_PERMISSION_DOMAIN: dict[str, str] = {
    "system": "core",
    "auth": "core",
    "storage": "core",
    "upload": "core",
    "preview": "core",
    "download": "core",
    "infra": "core",
    "performance": "core",
    "audit": "audit",
}


def resolve_group_domain(group: str) -> str:
    return GROUP_PERMISSION_DOMAIN.get(group, "core")


def build_config_permission(group: str, action: str) -> str:
    domain = resolve_group_domain(group)
    return f"cfg:{domain}:{action}"


def list_known_groups() -> list[str]:
    return sorted({spec.group for spec in REGISTRY.values()})
