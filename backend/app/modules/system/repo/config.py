from __future__ import annotations

from datetime import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.system.models.config import ConfigEntry


class ConfigRepository:
    @staticmethod
    async def get_global_entry(db: AsyncSession, key: str) -> ConfigEntry | None:
        stmt = select(ConfigEntry).where(
            ConfigEntry.scope_type == "GLOBAL",
            ConfigEntry.scope_id.is_(None),
            ConfigEntry.key == key,
        )
        return (await db.exec(stmt)).first()

    @staticmethod
    async def list_global_entries_by_keys(
        db: AsyncSession,
        keys: list[str],
    ) -> dict[str, ConfigEntry]:
        if not keys:
            return {}
        stmt = select(ConfigEntry).where(
            ConfigEntry.scope_type == "GLOBAL",
            ConfigEntry.scope_id.is_(None),
            ConfigEntry.key.in_(keys),
        )
        rows = (await db.exec(stmt)).all()
        return {row.key: row for row in rows}

    @staticmethod
    async def upsert_global_entry(
        db: AsyncSession,
        *,
        key: str,
        value: str,
        value_type: str,
        description: str,
        is_secret: bool,
        updated_by: int | None,
    ) -> ConfigEntry:
        now = datetime.now()
        entry = await ConfigRepository.get_global_entry(db, key)
        if entry:
            entry.value = value
            entry.value_type = value_type
            entry.description = description
            entry.is_secret = is_secret
            entry.updated_at = now
            entry.updated_by = updated_by
            return entry

        entry = ConfigEntry(
            scope_type="GLOBAL",
            scope_id=None,
            key=key,
            value=value,
            value_type=value_type,
            description=description,
            is_secret=is_secret,
            created_at=now,
            updated_at=now,
            updated_by=updated_by,
        )
        db.add(entry)
        return entry

    @staticmethod
    async def ensure_default_entry(
        db: AsyncSession,
        *,
        key: str,
        value: str,
        value_type: str,
        description: str,
        is_secret: bool,
        updated_by: int | None,
    ) -> None:
        entry = await ConfigRepository.get_global_entry(db, key)
        now = datetime.now()
        if entry:
            if not entry.value_type:
                entry.value_type = value_type
            if not entry.description:
                entry.description = description
            entry.is_secret = is_secret
            entry.updated_at = now
            if updated_by is not None:
                entry.updated_by = updated_by
            return

        db.add(
            ConfigEntry(
                scope_type="GLOBAL",
                scope_id=None,
                key=key,
                value=value,
                value_type=value_type,
                description=description,
                is_secret=is_secret,
                created_at=now,
                updated_at=now,
                updated_by=updated_by,
            )
        )
