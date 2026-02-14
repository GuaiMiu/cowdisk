from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from urllib.parse import urlparse
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlmodel.ext.asyncio.session import AsyncSession

from app.audit.constants import AUDIT_OUTBOX_EVENT_TYPE, AuditOutboxStatus
from app.audit.models import AuditOutbox
from app.core.audit_context import get_audit_context
from app.core.config import settings
from app.core.exception import ServiceException
from app.modules.system.repo.config import ConfigRepository
from app.modules.system.service.providers import (
    DefaultConfigProvider,
    DynamicConfigProvider,
    InstalledStateResolver,
    ProviderResult,
    StaticConfigProvider,
)
from app.modules.system.typed.config import Config, ConfigProvider
from app.modules.system.typed.keys import SECRET_MASK
from app.modules.system.typed.specs import ConfigSpec, GROUPS, REGISTRY


class DistributedConfigCache(Protocol):
    async def publish_invalidation(
        self,
        *,
        keys: list[str],
        groups: list[str],
        version: int,
    ) -> None: ...


class NoopDistributedConfigCache:
    async def publish_invalidation(
        self,
        *,
        keys: list[str],
        groups: list[str],
        version: int,
    ) -> None:
        return None


@dataclass(frozen=True)
class ConfigReadResult:
    key: str
    value: Any
    origin_source: str
    served_from: str


@dataclass(frozen=True)
class ConfigBatchUpdateResult:
    updated_keys: list[str]
    skipped_keys: list[str]
    version: int
    rollback_point: str | None


class _ProcessCache:
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._items: dict[str, tuple[float, tuple[Any, str]]] = {}

    def get(self, key: str) -> tuple[Any, str] | None:
        cached = self._items.get(key)
        if not cached:
            return None
        expires_at, payload = cached
        if time.monotonic() > expires_at:
            self._items.pop(key, None)
            return None
        return payload

    def set(self, key: str, value: Any, origin_source: str) -> None:
        self._items[key] = (time.monotonic() + self._ttl_seconds, (value, origin_source))

    def clear(self, *, key: str | None = None, group: str | None = None) -> None:
        if key:
            self._items.pop(key, None)
            return
        if group:
            keys = [
                spec_key
                for spec_key, spec in REGISTRY.items()
                if spec.group == group
            ]
            for spec_key in keys:
                self._items.pop(spec_key, None)
            return
        self._items.clear()


class ConfigCenterService:
    CACHE_TTL_SECONDS = 30

    _process_cache = _ProcessCache(ttl_seconds=CACHE_TTL_SECONDS)
    _config_version = 0
    _distributed_cache: DistributedConfigCache = NoopDistributedConfigCache()

    def __init__(
        self,
        db: AsyncSession,
        *,
        request_cache: dict[str, Any] | None = None,
    ) -> None:
        self._db = db
        self._request_cache = request_cache if request_cache is not None else {}
        self._installed_resolver = InstalledStateResolver()
        self._dynamic_provider = DynamicConfigProvider(
            db,
            deserialize_raw=self._deserialize_raw,
            validate_value=self._validate_value,
        )
        self._static_provider = StaticConfigProvider(
            validate_value=self._validate_value,
            resolve_env=self._resolve_env,
            installed_resolver=self._installed_resolver,
        )
        self._default_provider = DefaultConfigProvider()

    @staticmethod
    def _request_cache_key(spec_key: str) -> str:
        return f"cfg::{spec_key}"

    def _read_request_cache(self, spec_key: str) -> tuple[Any, str] | None:
        cached = self._request_cache.get(self._request_cache_key(spec_key))
        if not cached or not isinstance(cached, tuple) or len(cached) != 2:
            return None
        return cached

    def _write_request_cache(self, spec_key: str, value: Any, origin_source: str) -> None:
        self._request_cache[self._request_cache_key(spec_key)] = (value, origin_source)

    @classmethod
    def set_distributed_cache(cls, distributed_cache: DistributedConfigCache) -> None:
        cls._distributed_cache = distributed_cache

    @classmethod
    def clear_cache(
        cls,
        *,
        key: str | None = None,
        group: str | None = None,
    ) -> None:
        cls._process_cache.clear(key=key, group=group)

    @staticmethod
    def _serialize_value(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _deserialize_raw(raw: str) -> Any:
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return raw

    @staticmethod
    def _resolve_env(spec: ConfigSpec) -> Any:
        if spec.env_key:
            return getattr(settings, spec.env_key, None)
        fallback = spec.key.replace(".", "_").upper()
        return getattr(settings, fallback, None)

    @classmethod
    def _normalize_value(cls, value: Any, spec: ConfigSpec) -> Any:
        value_type = spec.value_type
        if value_type == "int":
            if isinstance(value, bool):
                raise ValueError("类型必须为整数")
            if isinstance(value, int):
                return value
            if isinstance(value, float):
                return int(value)
            if isinstance(value, str):
                stripped = value.strip()
                if not stripped:
                    raise ValueError("类型必须为整数")
                return int(stripped)
            raise ValueError("类型必须为整数")
        if value_type == "bool":
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return bool(value)
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"1", "true", "yes", "on"}:
                    return True
                if lowered in {"0", "false", "no", "off"}:
                    return False
            raise ValueError("类型必须为布尔值")
        if value_type == "json":
            if isinstance(value, (dict, list)):
                return value
            if isinstance(value, str):
                return json.loads(value)
            raise ValueError("类型必须为 JSON")
        if value is None:
            return ""
        return str(value)

    @staticmethod
    def _validate_rules(value: Any, spec: ConfigSpec) -> None:
        rules = spec.rules or {}
        if "enum" in rules and value not in rules["enum"]:
            raise ValueError(f"值必须为 {rules['enum']}")

        if isinstance(value, str):
            if "min_len" in rules and len(value) < int(rules["min_len"]):
                raise ValueError(f"长度不能小于 {rules['min_len']}")
            if "max_len" in rules and len(value) > int(rules["max_len"]):
                raise ValueError(f"长度不能大于 {rules['max_len']}")
            if rules.get("url_or_empty") and value:
                # 支持完整 URL 或站内相对路径（用于 Logo 等静态资源）。
                if value.startswith("/"):
                    pass
                else:
                    parsed = urlparse(value)
                    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                        raise ValueError("URL 格式不正确")
            if rules.get("timezone"):
                try:
                    ZoneInfo(value)
                except Exception:
                    allowed = {"Asia/Shanghai", "UTC", "Etc/UTC", "Asia/Beijing"}
                    if value not in allowed:
                        raise ValueError("时区格式不正确")
            if "regex" in rules:
                if not re.fullmatch(str(rules["regex"]), value):
                    raise ValueError("格式不正确")

        if isinstance(value, int):
            if "min" in rules and value < int(rules["min"]):
                raise ValueError(f"值不能小于 {rules['min']}")
            if "max" in rules and value > int(rules["max"]):
                raise ValueError(f"值不能大于 {rules['max']}")

    @classmethod
    def _validate_value(cls, spec: ConfigSpec, value: Any) -> Any:
        normalized = cls._normalize_value(value, spec)
        cls._validate_rules(normalized, spec)
        return normalized

    async def _read_registry_value(self, spec: ConfigSpec) -> ConfigReadResult:
        request_cached = self._read_request_cache(spec.key)
        if request_cached is not None:
            value, origin_source = request_cached
            return ConfigReadResult(
                key=spec.key,
                value=value,
                origin_source=origin_source,
                served_from="request_cache",
            )

        process_cached = self._process_cache.get(spec.key)
        if process_cached is not None:
            value, origin_source = process_cached
            result = ConfigReadResult(
                key=spec.key,
                value=value,
                origin_source=origin_source,
                served_from="process_cache",
            )
            self._write_request_cache(spec.key, value, origin_source)
            return result

        provider_result: ProviderResult | None = await self._dynamic_provider.read(spec)
        if provider_result is None:
            provider_result = await self._static_provider.read(spec)
        if provider_result is None:
            provider_result = self._default_provider.read(spec)

        self._process_cache.set(spec.key, provider_result.value, provider_result.origin_source)
        self._write_request_cache(spec.key, provider_result.value, provider_result.origin_source)
        return ConfigReadResult(
            key=spec.key,
            value=provider_result.value,
            origin_source=provider_result.origin_source,
            served_from="direct",
        )

    async def get(self, key: str) -> ConfigReadResult:
        spec = REGISTRY.get(key)
        if not spec:
            raise ServiceException(msg=f"未知配置项: {key}")
        return await self._read_registry_value(spec)

    async def get_value(self, key: str) -> Any:
        return (await self.get(key)).value

    async def is_installed(self) -> bool:
        return await self._installed_resolver.is_installed()

    async def ensure_defaults(
        self,
        *,
        overrides: dict[str, Any] | None = None,
        updated_by: int | None = None,
    ) -> None:
        overrides = overrides or {}
        for spec in REGISTRY.values():
            if spec.allow_env_after_install:
                continue
            value = overrides.get(spec.key, spec.default)
            try:
                normalized = self._validate_value(spec, value)
            except ValueError as exc:
                raise ServiceException(msg=f"{spec.key} 校验失败: {exc}") from exc
            await ConfigRepository.ensure_default_entry(
                self._db,
                key=spec.key,
                value=self._serialize_value(normalized),
                value_type=spec.value_type,
                description=spec.description,
                is_secret=spec.is_secret,
                updated_by=updated_by,
            )
        await self._db.commit()

    async def list_groups(self) -> list[str]:
        return list(GROUPS)

    async def list_group_specs_with_values(self, group: str) -> list[dict[str, Any]]:
        specs = [spec for spec in REGISTRY.values() if spec.group == group]
        if not specs:
            raise ServiceException(msg=f"未知配置分组: {group}")

        output: list[dict[str, Any]] = []
        for spec in specs:
            current = await self._read_registry_value(spec)
            value = current.value
            default = spec.default
            if spec.is_secret:
                value = SECRET_MASK
                default = SECRET_MASK
            output.append(
                {
                    "key": spec.key,
                    "group": spec.group,
                    "description": spec.description,
                    "value": value,
                    "default": default,
                    "value_type": spec.value_type,
                    "rules": spec.rules or {},
                    "is_secret": spec.is_secret,
                    "editable": spec.editable,
                    "source": current.origin_source,
                    "served_from": current.served_from,
                }
            )
        return output

    async def update_batch(
        self,
        *,
        items: list[dict[str, Any]],
        updated_by: int | None,
    ) -> ConfigBatchUpdateResult:
        if not items:
            return ConfigBatchUpdateResult(
                updated_keys=[],
                skipped_keys=[],
                version=type(self)._config_version,
                rollback_point=None,
            )

        keys = [str(item.get("key", "")).strip() for item in items]
        entries = await ConfigRepository.list_global_entries_by_keys(self._db, keys)

        errors: list[dict[str, str]] = []
        normalized_items: list[tuple[ConfigSpec, Any, Any, str]] = []
        skipped_keys: list[str] = []

        for item in items:
            key = str(item.get("key", "")).strip()
            value = item.get("value")
            spec = REGISTRY.get(key)
            if not spec:
                errors.append({"key": key, "error": "未知配置项"})
                continue
            if not spec.editable:
                errors.append({"key": key, "error": "该配置项不可编辑"})
                continue

            entry = entries.get(key)
            old_value = spec.default
            if entry:
                try:
                    old_value = self._validate_value(spec, self._deserialize_raw(entry.value))
                except Exception:
                    old_value = spec.default

            if spec.is_secret and value == SECRET_MASK:
                skipped_keys.append(key)
                continue

            try:
                normalized = self._validate_value(spec, value)
            except Exception as exc:
                errors.append({"key": key, "error": str(exc)})
                continue

            normalized_items.append((spec, old_value, normalized, key))

        if errors:
            raise ServiceException(
                msg="配置校验失败",
                data=json.dumps(errors, ensure_ascii=False),
            )

        updated_keys: list[str] = []
        changed_groups: set[str] = set()
        audit_changes: list[dict[str, Any]] = []

        for spec, old_value, new_value, key in normalized_items:
            if old_value == new_value:
                skipped_keys.append(key)
                continue

            await ConfigRepository.upsert_global_entry(
                self._db,
                key=spec.key,
                value=self._serialize_value(new_value),
                value_type=spec.value_type,
                description=spec.description,
                is_secret=spec.is_secret,
                updated_by=updated_by,
            )
            updated_keys.append(spec.key)
            changed_groups.add(spec.group)
            audit_changes.append(
                {
                    "key": spec.key,
                    "group": spec.group,
                    "from": SECRET_MASK if spec.is_secret else old_value,
                    "to": SECRET_MASK if spec.is_secret else new_value,
                }
            )

        if not updated_keys:
            await self._db.rollback()
            return ConfigBatchUpdateResult(
                updated_keys=[],
                skipped_keys=skipped_keys,
                version=self._config_version,
                rollback_point=None,
            )

        rollback_point = f"cfg-rb-{int(datetime.now().timestamp())}-{uuid4().hex[:8]}"
        await self._enqueue_change_outbox(updated_by=updated_by, changes=audit_changes)
        await self._db.commit()

        for key in updated_keys:
            self.clear_cache(key=key)
        for group in changed_groups:
            self.clear_cache(group=group)

        type(self)._config_version += 1
        await self._distributed_cache.publish_invalidation(
            keys=updated_keys,
            groups=sorted(changed_groups),
            version=type(self)._config_version,
        )

        return ConfigBatchUpdateResult(
            updated_keys=updated_keys,
            skipped_keys=skipped_keys,
            version=type(self)._config_version,
            rollback_point=rollback_point,
        )

    async def _enqueue_change_outbox(
        self,
        *,
        updated_by: int | None,
        changes: list[dict[str, Any]],
    ) -> None:
        context = get_audit_context()
        payload = {
            "event_id": uuid4().hex,
            "action": "CONFIG_UPDATE",
            "status": "SUCCESS",
            "resource_type": "CONFIG",
            "resource_id": None,
            "path": "/admin/system/config/batch",
            "user_id": updated_by or context.user_id,
            "ip": context.ip,
            "user_agent": context.user_agent,
            "request_id": context.request_id,
            "trace_id": context.trace_id,
            "duration_ms": None,
            "detail": {
                "changes": changes,
                "count": len(changes),
            },
            "created_at": datetime.now().isoformat(),
        }
        self._db.add(
            AuditOutbox(
                event_type=AUDIT_OUTBOX_EVENT_TYPE,
                payload_json=json.dumps(payload, ensure_ascii=False),
                status=AuditOutboxStatus.PENDING,
                attempts=0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )


class RequestConfigProvider(ConfigProvider):
    def __init__(self, service: ConfigCenterService) -> None:
        self._service = service

    async def get_value(self, key: str) -> Any:
        return await self._service.get_value(key)


def build_runtime_config(
    db: AsyncSession | None = None,
    *,
    service: ConfigCenterService | None = None,
    request_cache: dict[str, Any] | None = None,
) -> Config:
    runtime_service = service
    if runtime_service is None:
        if db is None:
            raise ValueError("db 与 service 不能同时为空")
        runtime_service = ConfigCenterService(db, request_cache=request_cache)
    provider = RequestConfigProvider(runtime_service)
    return Config(provider=provider)
