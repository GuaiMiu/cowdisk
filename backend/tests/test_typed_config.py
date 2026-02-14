from __future__ import annotations

import json
from pathlib import Path

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
import pytest

from app.core.config import settings
from app.core.exception import ServiceException
from app.modules.system.repo.config import ConfigRepository
from app.modules.system.service.config import ConfigCenterService
from app.modules.system.typed.keys import ConfigKey, SECRET_MASK


@pytest_asyncio.fixture
async def db_session(tmp_path: Path):
    db_path = tmp_path / "test_config.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_read_priority_db_over_env_and_default(db_session):
    ConfigCenterService.clear_cache()
    old_install_completed = settings.INSTALL_COMPLETED

    try:
        settings.INSTALL_COMPLETED = False
        settings.DISK_ROOT = "env-storage"
        service = ConfigCenterService(db_session, request_cache={})

        value_from_env = await service.get_value(ConfigKey.STORAGE_PATH)
        assert value_from_env == "env-storage"

        await service.update_batch(
            items=[{"key": ConfigKey.STORAGE_PATH, "value": "db-storage"}],
            updated_by=1,
        )

        ConfigCenterService.clear_cache()
        service2 = ConfigCenterService(db_session, request_cache={})
        value_from_db = await service2.get_value(ConfigKey.STORAGE_PATH)
        assert value_from_db == "db-storage"

        default_value = await service2.get_value(ConfigKey.SYSTEM_SITE_NAME)
        assert default_value == "笨牛网盘"
    finally:
        settings.INSTALL_COMPLETED = old_install_completed


@pytest.mark.asyncio
async def test_update_validation_failure(db_session):
    ConfigCenterService.clear_cache()
    service = ConfigCenterService(db_session, request_cache={})

    with pytest.raises(ServiceException) as exc:
        await service.update_batch(
            items=[{"key": ConfigKey.SYSTEM_MAX_SINGLE_FILE_MB, "value": 0}],
            updated_by=1,
        )

    assert exc.value.msg == "配置校验失败"
    errors = json.loads(exc.value.data or "[]")
    assert errors[0]["key"] == ConfigKey.SYSTEM_MAX_SINGLE_FILE_MB


@pytest.mark.asyncio
async def test_secret_mask_update_keeps_value(db_session):
    ConfigCenterService.clear_cache()
    service = ConfigCenterService(db_session, request_cache={})

    await service.update_batch(
        items=[{"key": ConfigKey.AUTH_JWT_SECRET_KEY, "value": "super-secret"}],
        updated_by=7,
    )

    listed = await service.list_group_specs_with_values("auth")
    secret_row = next(item for item in listed if item["key"] == ConfigKey.AUTH_JWT_SECRET_KEY)
    assert secret_row["value"] == SECRET_MASK

    result = await service.update_batch(
        items=[{"key": ConfigKey.AUTH_JWT_SECRET_KEY, "value": SECRET_MASK}],
        updated_by=7,
    )
    assert ConfigKey.AUTH_JWT_SECRET_KEY in result.skipped_keys

    entry = await ConfigRepository.get_global_entry(db_session, ConfigKey.AUTH_JWT_SECRET_KEY)
    assert entry is not None
    assert json.loads(entry.value) == "super-secret"


@pytest.mark.asyncio
async def test_request_scope_cache_hit(db_session, monkeypatch):
    ConfigCenterService.clear_cache()
    service = ConfigCenterService(db_session, request_cache={})
    await service.update_batch(
        items=[{"key": ConfigKey.SYSTEM_DEFAULT_USER_QUOTA_GB, "value": 55}],
        updated_by=1,
    )

    ConfigCenterService.clear_cache(key=ConfigKey.SYSTEM_DEFAULT_USER_QUOTA_GB)

    counter = {"count": 0}

    original_get = ConfigRepository.get_global_entry

    async def wrapped_get(db, key):
        counter["count"] += 1
        return await original_get(db, key)

    monkeypatch.setattr(ConfigRepository, "get_global_entry", wrapped_get)

    cached_service = ConfigCenterService(db_session, request_cache={})
    value1 = await cached_service.get_value(ConfigKey.SYSTEM_DEFAULT_USER_QUOTA_GB)
    value2 = await cached_service.get_value(ConfigKey.SYSTEM_DEFAULT_USER_QUOTA_GB)

    assert value1 == 55
    assert value2 == 55
    assert counter["count"] == 1


@pytest.mark.asyncio
async def test_env_fallback_after_install_only_static_keys(db_session):
    ConfigCenterService.clear_cache()
    old_install_completed = settings.INSTALL_COMPLETED
    try:
        settings.INSTALL_COMPLETED = True
        service = ConfigCenterService(db_session, request_cache={})

        settings.JWT_SECRET_KEY = "env-only-secret"
        settings.REDIS_HOST = "10.0.0.1"
        ConfigCenterService.clear_cache()

        value_auth = await service.get_value(ConfigKey.AUTH_JWT_SECRET_KEY)
        value_redis_host = await service.get_value(ConfigKey.REDIS_HOST)

        assert value_auth == ""
        assert value_redis_host == "10.0.0.1"
    finally:
        settings.INSTALL_COMPLETED = old_install_completed
