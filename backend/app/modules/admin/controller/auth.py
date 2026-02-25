"""
@File: auth.py
@Author: GuaiMiu
@Date: 2025/3/19 14:48
@Version: 1.0
@Description:
"""

from typing import Annotated

from fastapi import APIRouter, Request
from fastapi.params import Cookie, Depends
from fastapi.security import OAuth2PasswordRequestForm
from redis import asyncio as aioredis
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_redis, get_async_session
from app.core.response import ApiResponse, ok
from app.modules.admin.models.user import User
from app.modules.admin.schemas.auth import (
    TokenOut,
    UserProfileUpdateIn,
    UserRegisterIn,
)
from app.modules.admin.schemas.menu import MenuRoutersOut
from app.modules.admin.schemas.user import UserOut
from app.modules.admin.services.auth import AuthService, get_user_permissions, oauth2_scheme
from app.modules.system.deps import get_config
from app.modules.system.typed.config import Config
from app.shared.deps import require_user
from app.utils.logger import logger

auth_router = APIRouter(prefix="/auth", tags=["Admin - Auth"])


def _set_auth_cookies(result, request: Request, *, session_id: str, refresh_token: str) -> None:
    cookie_kwargs = {
        "httponly": True,
        "secure": request.url.scheme == "https",
        "samesite": "lax",
        "max_age": 7 * 24 * 60 * 60,
        "path": "/",
    }
    result.set_cookie(key="session_id", value=session_id, **cookie_kwargs)
    result.set_cookie(key="refresh_token", value=refresh_token, **cookie_kwargs)


@auth_router.post(
    "/register",
    summary="注册",
    response_model=ApiResponse[UserOut],
)
async def register(
    user: UserRegisterIn,
    db: AsyncSession = Depends(get_async_session),
    config: Config = Depends(get_config),
):
    db_user = await AuthService.register(db, user, config=config)
    return ok(UserOut.model_validate(db_user).model_dump(), message="注册成功")


@auth_router.post(
    "/login",
    summary="登录",
    response_model=ApiResponse[TokenOut],
)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(OAuth2PasswordRequestForm),
    db: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_async_redis),
):
    client_ip = request.client.host if request.client else ""
    token_bundle = await AuthService.login_session(
        db=db,
        redis=redis,
        username=form_data.username,
        password=form_data.password,
        client_ip=client_ip,
        user_agent=request.headers.get("user-agent"),
    )
    result = ok(
        TokenOut(access_token=token_bundle["access_token"], token_type="bearer").model_dump(),
        message="登录成功",
    )
    _set_auth_cookies(
        result,
        request,
        session_id=token_bundle["session_id"],
        refresh_token=token_bundle["refresh_token"],
    )
    return result


@auth_router.post("/refresh-token", summary="刷新token", response_model=ApiResponse[TokenOut])
async def refresh_token(
    request: Request,
    session_id: str = Cookie(None),
    refresh_token: str = Cookie(None),
    redis: aioredis.Redis = Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    client_ip = request.client.host if request.client else ""
    token_bundle = await AuthService.refresh_session(
        db=db,
        redis=redis,
        session_id=session_id,
        refresh_token=refresh_token,
        client_ip=client_ip,
        user_agent=request.headers.get("user-agent"),
    )
    result = ok(
        TokenOut(access_token=token_bundle["access_token"], token_type="bearer").model_dump(),
        message="刷新成功",
    )
    _set_auth_cookies(
        result,
        request,
        session_id=token_bundle["session_id"],
        refresh_token=token_bundle["refresh_token"],
    )
    return result


@auth_router.get(
    "/routers",
    summary="获取当前用户路由",
    response_model=ApiResponse[MenuRoutersOut],
)
async def get_router(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_user),
):
    routers = await AuthService.get_current_user_routers(db, current_user)
    return ok(routers)


@auth_router.get(
    "/permissions",
    summary="获取当前用户权限",
    response_model=ApiResponse[list[str]],
)
async def get_permissions(
    permissions: list[str] = Depends(get_user_permissions),
):
    return ok(AuthService.sanitize_permissions(permissions))


@auth_router.get(
    "/me",
    response_model=ApiResponse[UserOut],
    summary="获取当前用户信息",
)
async def get_me(
    current_user: User = Depends(require_user),
):
    return ok(AuthService.serialize_current_user(current_user))


@auth_router.patch(
    "/me",
    response_model=ApiResponse[UserOut],
    summary="更新当前用户信息",
)
async def update_me(
    payload: UserProfileUpdateIn,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_user),
):
    db_user = await AuthService.update_current_user_profile(
        db=db,
        current_user=current_user,
        payload=payload,
    )
    return ok(AuthService.serialize_current_user(db_user), message="更新成功")


@auth_router.post(
    "/logout",
    response_model=ApiResponse[dict],
    summary="退出",
)
async def logout(
    token: Annotated[str, Depends(oauth2_scheme)],
    redis: aioredis.Redis = Depends(get_async_redis),
):
    payload = AuthService.decode_access_token(token, verify_exp=False)
    session_id = payload.get("session_id", "")
    await AuthService.logout(redis=redis, session_id=session_id, user_id=payload.get("id"))
    result = ok({}, message="退出成功")
    result.delete_cookie(key="session_id", path="/")
    result.delete_cookie(key="refresh_token", path="/")
    logger.info("用户 %s 退出成功", payload.get("username", ""))
    return result


@auth_router.get("/devices", summary="查看登录设备", response_model=ApiResponse[list[dict]])
async def list_devices(
    user: User = Depends(require_user),
    redis: aioredis.Redis = Depends(get_async_redis),
):
    devices = await AuthService.list_login_devices(redis=redis, user_id=user.id)
    return ok(devices, message="设备列表获取成功")


@auth_router.get(
    "/request-info",
    summary="获取请求源信息",
    response_model=ApiResponse[dict],
)
async def get_ip(
    data=Depends(AuthService.get_request_info),
):
    return ok(data, message="获取请求源信息成功")
