from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.core.config import settings
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.system.repo.config import ConfigRepository
from app.modules.system.typed.specs import ConfigSpec, STATIC_ENV_KEYS
from app.utils.logger import logger

OriginSource = str


@dataclass(frozen=True)
class ProviderResult:
    value: Any
    origin_source: OriginSource


class InstalledStateResolver:
    async def is_installed(self) -> bool:
        value = settings.INSTALL_COMPLETED
        if isinstance(value, bool):
            return value
        if value in (None, ""):
            return False
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "yes", "on"}:
                return True
            if lowered in {"0", "false", "no", "off"}:
                return False
        logger.warning("INSTALL_COMPLETED 环境变量解析失败，回退 False")
        return False


class DynamicConfigProvider:
    def __init__(
        self,
        db: AsyncSession,
        *,
        deserialize_raw: Callable[[str], Any],
        validate_value: Callable[[ConfigSpec, Any], Any],
    ) -> None:
        self._db = db
        self._deserialize_raw = deserialize_raw
        self._validate_value = validate_value

    async def read(self, spec: ConfigSpec) -> ProviderResult | None:
        entry = await ConfigRepository.get_global_entry(self._db, spec.key)
        if not entry:
            return None
        raw = self._deserialize_raw(entry.value)
        try:
            parsed = self._validate_value(spec, raw)
        except Exception as exc:
            logger.warning(
                "配置值解析失败，已回退默认值: key=%s, raw=%s, err=%s",
                spec.key,
                raw,
                exc,
            )
            return ProviderResult(value=spec.default, origin_source="default")
        return ProviderResult(value=parsed, origin_source="db")


class StaticConfigProvider:
    def __init__(
        self,
        *,
        validate_value: Callable[[ConfigSpec, Any], Any],
        resolve_env: Callable[[ConfigSpec], Any],
        installed_resolver: InstalledStateResolver,
    ) -> None:
        self._validate_value = validate_value
        self._resolve_env = resolve_env
        self._installed_resolver = installed_resolver

    async def read(self, spec: ConfigSpec) -> ProviderResult | None:
        installed = await self._installed_resolver.is_installed()
        can_use_env = (not installed) or (spec.key in STATIC_ENV_KEYS)
        if not can_use_env:
            return None
        env_value = self._resolve_env(spec)
        if env_value in (None, ""):
            return None
        try:
            parsed_env = self._validate_value(spec, env_value)
        except Exception as exc:
            logger.warning(
                "环境变量解析失败，回退默认值: key=%s, env=%s, err=%s",
                spec.key,
                env_value,
                exc,
            )
            return ProviderResult(value=spec.default, origin_source="default")
        return ProviderResult(value=parsed_env, origin_source="env")


class DefaultConfigProvider:
    @staticmethod
    def read(spec: ConfigSpec) -> ProviderResult:
        return ProviderResult(value=spec.default, origin_source="default")
