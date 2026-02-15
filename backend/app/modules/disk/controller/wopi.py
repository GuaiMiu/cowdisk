"""
@File: wopi.py
@Author: GuaiMiu
@Date: 2026/2/15
@Version: 1.0
@Description: WOPI 协议接口（Collabora）
"""

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from redis import asyncio as aioredis
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_redis, get_async_session
from app.core.exception import ServiceException
from app.modules.disk.services.office import OfficeService

wopi_router = APIRouter(prefix="/wopi", tags=["Disk - WOPI"])


def _extract_access_token(access_token: str | None, authorization: str | None) -> str:
    if access_token:
        return access_token
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


@wopi_router.get("/files/{file_id}", summary="WOPI CheckFileInfo")
async def wopi_check_file_info(
    request: Request,
    file_id: int,
    access_token: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_async_redis),
):
    token = _extract_access_token(access_token, authorization)
    data = await OfficeService.get_wopi_check_file_info(
        db=db,
        file_id=file_id,
        token=token,
        redis=redis,
        request=request,
    )
    return data


@wopi_router.get("/files/{file_id}/contents", summary="WOPI GetFile")
async def wopi_get_file(
    request: Request,
    file_id: int,
    access_token: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_async_redis),
):
    token = _extract_access_token(access_token, authorization)
    return await OfficeService.get_wopi_file_response(
        db=db,
        file_id=file_id,
        token=token,
        redis=redis,
        request=request,
    )


@wopi_router.post("/files/{file_id}/contents", summary="WOPI PutFile")
async def wopi_put_file(
    request: Request,
    file_id: int,
    access_token: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
    x_wopi_override: str | None = Header(default=None, alias="X-WOPI-Override"),
    db: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_async_redis),
):
    token = _extract_access_token(access_token, authorization)
    override = (x_wopi_override or "").strip().upper()
    if override and override != "PUT":
        raise ServiceException(msg=f"不支持的 WOPI 操作: {override}")
    content = await request.body()
    result = await OfficeService.put_wopi_file_contents(
        db=db,
        file_id=file_id,
        token=token,
        redis=redis,
        content=content,
        request=request,
    )
    response = Response(status_code=200)
    response.headers["X-WOPI-ItemVersion"] = str(result.get("etag") or "")
    return response
