from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Annotated

from fastapi import Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_session
from app.modules.system.services.config import ConfigCenterService, build_runtime_config
from app.modules.system.typed.config import Config


@dataclass(frozen=True)
class ConfigContext:
    db: AsyncSession
    service: ConfigCenterService
    config: Config


async def get_db(db: AsyncSession = Depends(get_async_session)) -> AsyncSession:
    return db


def get_request_cache(request: Request) -> dict[str, Any]:
    cache = getattr(request.state, "_config_request_cache", None)
    if cache is None:
        cache = {}
        request.state._config_request_cache = cache
    return cache


async def get_config_context(
    db: AsyncSession = Depends(get_db),
    request_cache: dict[str, Any] = Depends(get_request_cache),
) -> ConfigContext:
    service = ConfigCenterService(db, request_cache=request_cache)
    config = build_runtime_config(service=service)
    return ConfigContext(db=db, service=service, config=config)


async def get_config_service(
    context: ConfigContext = Depends(get_config_context),
) -> ConfigCenterService:
    return context.service


async def get_config(
    context: ConfigContext = Depends(get_config_context),
) -> Config:
    return context.config


ConfigDep = Annotated[Config, Depends(get_config)]
ConfigServiceDep = Annotated[ConfigCenterService, Depends(get_config_service)]
ConfigContextDep = Annotated[ConfigContext, Depends(get_config_context)]

