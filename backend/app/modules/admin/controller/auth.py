"""
@File: auth.py
@Author: GuaiMiu
@Date: 2025/3/19 14:48
@Version: 1.0
@Description:
"""

import secrets
import json
from typing import Annotated

from fastapi import APIRouter, Request
from fastapi.params import Depends, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from redis import asyncio as aioredis
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.admin.schemas.menu import MenuRoutersOut
from app.modules.admin.schemas.user import UserOut
from app.core.config import settings
from app.core.database import get_async_redis, get_async_session
from app.core.exception import AuthException, LoginException, ServiceException
from app.modules.admin.dao.user import user_crud
from app.modules.admin.models.response import ResponseModel
from app.modules.admin.models.user import User
from app.modules.admin.schemas.auth import TokenOut, TokenPayload
from app.modules.admin.schemas.auth import (
    UserRegisterIn,
    UserLoginIn,
    UserProfileUpdateIn,
)
from app.modules.admin.services.auth import AuthService, get_user_permissions, oauth2_scheme
from app.modules.system.deps import get_config
from app.modules.system.typed.config import Config
from app.shared.deps import require_user
from app.utils.logger import logger
from app.utils.response import Res

auth_router = APIRouter(prefix="/auth", tags=["Admin - Auth"])


@auth_router.post(
    "/register",
    summary="注册",
    description="哪有那么多描述，单纯的注册接口",
    response_model=ResponseModel[UserOut],
    responses={422: {"model": ResponseModel[str]}},
)
async def register(
    user: UserRegisterIn,
    db: AsyncSession = Depends(get_async_session),
    config: Config = Depends(get_config),
):
    db_user = await AuthService.register(db, user, config=config)
    return Res.success(data=UserOut.model_validate(db_user))


@auth_router.post(
    "/login",
    summary="登录",
    description="哪有那么多描述，单纯的登录接口",
    response_model=ResponseModel[TokenOut],
    responses={422: {"model": ResponseModel[str]}},
)
async def login(
    request: Request,
    # user: UserLoginIn,
    form_data: OAuth2PasswordRequestForm = Depends(OAuth2PasswordRequestForm),
    db: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_async_redis),
):
    client_ip = request.client.host if request.client else ""
    allowed = await AuthService.apply_rate_limit(
        redis,
        action="login",
        identifier=client_ip or "unknown",
        limit=settings.AUTH_LOGIN_RATE_LIMIT,
        window_seconds=settings.AUTH_LOGIN_RATE_WINDOW,
    )
    if not allowed:
        logger.warning("登录限流触发 ip=%s", client_ip)
        raise LoginException(msg="登录过于频繁，请稍后重试")

    if not form_data.username or not form_data.password:
        raise LoginException(msg=f"用户名或密码错误，请重新登录")
    try:
        user = UserLoginIn(
            username=form_data.username,
            password=form_data.password,
        )
    except ValidationError as exc:
        return Res.error(msg="登录参数校验失败", data=exc.errors(), status_code=422)
    db_user = await AuthService.login(
        db=db,
        redis=redis,
        login_user=user,
        client_ip=client_ip,
    )
    # 生成token
    session_id = secrets.token_urlsafe(32)
    refresh_token = AuthService.create_refresh_token()
    token = await AuthService.create_access_token(
        TokenPayload(id=db_user.id, session_id=session_id, username=db_user.username)
    )
    await AuthService.bind_session(
        redis,
        user_id=db_user.id,
        session_id=session_id,
        access_token=token,
        refresh_token=refresh_token,
        user_agent=request.headers.get("user-agent"),
        login_ip=client_ip,
    )

    result = Res.success(
        msg="登录成功", data=TokenOut(access_token=token, token_type="bearer")
    )
    result.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )
    result.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )
    return result


@auth_router.post("/refresh-token", summary="刷新token")
async def refresh_token(
    request: Request,
    session_id: str = Cookie(None),
    refresh_token: str = Cookie(None),
    redis: aioredis.Redis = Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    client_ip = request.client.host if request.client else ""
    allowed = await AuthService.apply_rate_limit(
        redis,
        action="refresh",
        identifier=client_ip or "unknown",
        limit=settings.AUTH_REFRESH_RATE_LIMIT,
        window_seconds=settings.AUTH_REFRESH_RATE_WINDOW,
    )
    if not allowed:
        logger.warning("刷新限流触发 ip=%s", client_ip)
        raise AuthException(msg="刷新过于频繁，请稍后重试")

    if not session_id or not refresh_token:
        raise AuthException(msg="请先登录")

    user_id = await AuthService.get_refresh_user_id(
        redis,
        session_id=session_id,
        refresh_token=refresh_token,
    )
    if not user_id:
        raise AuthException(msg="请先登录")

    fingerprint_ok = await AuthService.validate_session_fingerprint(
        redis,
        session_id=session_id,
        user_agent=request.headers.get("user-agent"),
        login_ip=client_ip,
    )
    if not fingerprint_ok:
        logger.warning("refresh 指纹校验失败 user_id=%s ip=%s", user_id, client_ip)
        raise AuthException(msg="检测到登录环境变更，请重新登录")

    rotate_allowed = await AuthService.apply_refresh_rotate_limit(
        redis,
        user_id=int(user_id),
    )
    if not rotate_allowed:
        logger.warning("refresh 轮换次数超限 user_id=%s ip=%s", user_id, client_ip)
        raise AuthException(msg="刷新次数过多，请重新登录")

    new_session_id = secrets.token_urlsafe(32)
    db_user = await user_crud.get_by_id(db, user_id)
    if not db_user:
        raise AuthException(msg="用户不存在，请重新登录")
    next_refresh_token = AuthService.create_refresh_token()
    token = await AuthService.create_access_token(
        TokenPayload(
            id=db_user.id, session_id=new_session_id, username=db_user.username
        )
    )
    await AuthService.bind_session(
        redis,
        user_id=db_user.id,
        session_id=new_session_id,
        access_token=token,
        refresh_token=next_refresh_token,
        user_agent=request.headers.get("user-agent"),
        login_ip=client_ip,
    )
    await AuthService.purge_session(
        redis,
        session_id=session_id,
        user_id=db_user.id,
    )
    result = Res.success(
        msg="刷新成功",
        data=TokenOut(access_token=token, token_type="bearer"),
    )
    result.set_cookie(
        key="session_id",
        value=new_session_id,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )
    result.set_cookie(
        key="refresh_token",
        value=next_refresh_token,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )
    return result


@auth_router.get(
    "/routers",
    summary="获取当前用户路由",
    response_model=ResponseModel[MenuRoutersOut],
)
async def get_router(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_user),
):
    """

    :param db:
    :param current_user:
    :return:
    """
    routers = await AuthService.get_current_user_routers(db, current_user)
    return ResponseModel.success(data=routers)


@auth_router.get(
    "/permissions",
    summary="获取当前用户权限",
    response_model=ResponseModel[list[str]],
)
async def get_permissions(
    permissions: list[str] = Depends(get_user_permissions),
):
    """
    获取当前用户权限
    """
    cleaned = [perm for perm in permissions if isinstance(perm, str)]
    return ResponseModel.success(data=cleaned)


@auth_router.get(
    "/me",
    response_model=ResponseModel[UserOut],
    summary="获取当前用户信息",
)
async def get_me(
    current_user: User = Depends(require_user),
):
    """
    获取当前用户信息
    :return:
    """
    data = UserOut.model_validate(current_user).model_dump(exclude={"roles"})
    return Res.success(data=data)


@auth_router.patch(
    "/me",
    response_model=ResponseModel[UserOut],
    summary="更新当前用户信息",
)
async def update_me(
    payload: UserProfileUpdateIn,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_user),
):
    db_user = await user_crud.get_by_id(db, current_user.id)
    if not db_user:
        raise ServiceException(msg="用户不存在")

    if payload.mail is not None and payload.mail != db_user.mail:
        exists = await user_crud.get_by_field(db, "mail", payload.mail)
        if exists and exists.id != db_user.id:
            raise ServiceException(msg=f"邮箱 {payload.mail} 已被使用")
        db_user.mail = payload.mail

    if payload.nickname is not None:
        db_user.nickname = payload.nickname

    if payload.new_password is not None:
        if not db_user.verify_password(payload.current_password or ""):
            raise ServiceException(msg="当前密码不正确")
        db_user.password = User.create_password(payload.new_password)

    db_user.update_by = db_user.username
    db_user = await user_crud.update(db, db_user)
    data = UserOut.model_validate(db_user).model_dump(exclude={"roles"})
    return Res.success(data=data, msg="更新成功")


@auth_router.post(
    "/logout",
    response_model=ResponseModel,
    summary="退出",
)
async def logout(
    token: Annotated[str, Depends(oauth2_scheme)],
    redis: aioredis.Redis = Depends(get_async_redis),
):
    """
    登出
    :param token:
    :param redis:
    :return:
    """
    payload = AuthService.decode_access_token(token, verify_exp=False)
    session_id = payload.get("session_id", "")
    await AuthService.logout(redis=redis, session_id=session_id, user_id=payload.get("id"))
    result = Res.success(msg="退出成功")
    result.delete_cookie(key="session_id", path="/")
    result.delete_cookie(key="refresh_token", path="/")
    logger.info(f"用户 {payload.get('username', '')} 退出成功")
    return result


@auth_router.get("/devices", summary="查看登录设备")
async def list_devices(
    user: User = Depends(require_user),
    redis: aioredis.Redis = Depends(get_async_redis),
):
    session_ids = await redis.smembers(
        AuthService._user_sessions_key(user.id)
    )
    devices = []

    for sid in session_ids:
        session_id = sid.decode("utf-8") if isinstance(sid, bytes) else str(sid)
        device_key = AuthService._device_info_key(session_id)
        device_info = await redis.get(device_key)
        if device_info:
            try:
                info = (
                    json.loads(device_info) if isinstance(device_info, str) else device_info
                )
            except json.JSONDecodeError:
                await redis.srem(AuthService._user_sessions_key(user.id), sid)
                await redis.delete(device_key)
                continue
            devices.append(
                {
                    "session_id": session_id,
                    "user_agent": info.get("user_agent"),
                    "login_ip": info.get("login_ip"),
                }
            )
        else:
            # 如果 device_info 没了，就清理掉这条无效 session
            await redis.srem(AuthService._user_sessions_key(user.id), sid)

    return Res.success(data=devices, msg="设备列表获取成功")


@auth_router.get(
    "/request-info", summary="获取请求源信息", response_model=ResponseModel[dict]
)
async def get_ip(
    data=Depends(AuthService.get_request_info),
):
    """
    获取请求源信息
    :param data:
    :return:
    """

    return Res.success(data=data, msg="获取请求源信息成功")



