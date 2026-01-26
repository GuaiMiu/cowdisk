"""
@File: auth.py
@Author: GuaiMiu
@Date: 2025/3/19 14:48
@Version: 1.0
@Description:
"""

import secrets
from datetime import timedelta
from typing import Annotated

import jwt
from fastapi import APIRouter, Request, Response
from fastapi.params import Depends, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from redis import asyncio as aioredis
from sqlmodel.ext.asyncio.session import AsyncSession

from app.admin.schemas.menu import MenuRoutersOut
from app.admin.schemas.user import UserOut
from app.core.config import settings
from app.core.database import get_async_redis, get_async_session
from app.core.exception import AuthException, LoginException
from app.admin.dao.user import user_crud
from app.enum.redis import RedisInitKeyEnum
from app.admin.models.response import ResponseModel
from app.admin.models.user import User
from app.admin.schemas.auth import TokenOut, TokenPayload
from app.admin.schemas.auth import UserRegisterIn, UserLoginIn
from app.admin.services.auth import (
    AuthService,
    get_user_permissions,
    oauth2_scheme,
)
from app.utils.logger import logger
from app.utils.response import Res

auth_router = APIRouter(prefix="/auth", tags=["认证模块"])


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
):
    db_user = await AuthService.register(db, user)
    return Res.success(data=UserOut.model_validate(db_user))


@auth_router.post(
    "/login",
    summary="登录",
    description="哪有那么多描述，单纯的登录接口",
    response_model=ResponseModel[TokenOut] | TokenOut,
    responses={422: {"model": ResponseModel[str]}},
)
async def login(
    request: Request,
    # user: UserLoginIn,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(OAuth2PasswordRequestForm),
    db: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_async_redis),
):

    if not form_data.username and not form_data.password:
        raise LoginException(msg=f"用户名或密码错误，请重新登录")
    try:
        user = UserLoginIn(
            username=form_data.username,
            password=form_data.password,
        )
    except ValidationError as exc:
        return Res.error(msg="登录参数校验失败", data=exc.errors(), status_code=422)
    db_user = await AuthService.login(
        request=request, db=db, redis=redis, login_user=user
    )
    # 生成token
    session_id = secrets.token_urlsafe(32)
    token = await AuthService.create_access_token(
        TokenPayload(id=db_user.id, session_id=session_id, username=db_user.username)
    )
    await redis.set(
        f"{RedisInitKeyEnum.ACCESS_TOKEN.key}:{session_id}",
        token,
        ex=timedelta(minutes=settings.JWT_REDIS_EXPIRE_MINUTES),
    )

    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        # secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )
    # 设置refresh_token
    await redis.set(
        f"{RedisInitKeyEnum.REFRESH_TOKEN.key}:{session_id}",
        f"{db_user.id}",
        ex=7 * 24 * 60 * 60,
    )
    # 设置用户登录设备信息
    await redis.set(
        f"{RedisInitKeyEnum.DEVICE_INFO.key}:{session_id}",
        str(
            {
                "user_agent": request.headers.get("user-agent"),
                "login_ip": request.client.host,
                "user_id": db_user.id,
            }
        ),
        ex=7 * 24 * 60 * 60,
    )
    # 设置用户sessions
    await redis.sadd(f"{RedisInitKeyEnum.USER_SESSIONS.key}:{db_user.id}", session_id)
    # 如果是swagger或redoc请求，返回token
    if request.headers.get("referer", "xxx").endswith("docs") or request.headers.get(
        "referer", "xxx"
    ).endswith("redoc"):
        return TokenOut(access_token=token, token_type="bearer")
    else:
        return {
            "code": 200,
            "msg": "登录成功",
            "data": TokenOut(access_token=token, token_type="bearer"),
        }
        # return Res.success(
        #     msg="登录成功", data=TokenOut(access_token=token, token_type="bearer")
        # )


@auth_router.post("/refresh_token", summary="刷新token")
async def refresh_token(
    response: Response,
    request: Request,
    old_token: Annotated[str, Depends(oauth2_scheme)],
    session_id: str = Cookie(None),
    redis: aioredis.Redis = Depends(get_async_redis),
    db: AsyncSession = Depends(get_async_session),
):
    user_id = await redis.get(f"{RedisInitKeyEnum.REFRESH_TOKEN.key}:{session_id}")
    redis_old_token = await redis.get(
        f"{RedisInitKeyEnum.ACCESS_TOKEN.key}:{session_id}"
    )
    if not redis_old_token or redis_old_token != old_token:
        logger.warning(f"IP:{request.client.host} 尝试使用无效的Token刷新")
        # 这里可以拉黑IP
        raise AuthException(msg="想干嘛？")
    if not session_id or not user_id:
        raise AuthException(msg="请先登录")
    new_session_id = secrets.token_urlsafe(32)
    db_user = await user_crud.get_by_id(db, user_id)
    token = await AuthService.create_access_token(
        TokenPayload(
            id=db_user.id, session_id=new_session_id, username=db_user.username
        )
    )
    await redis.set(
        f"{RedisInitKeyEnum.ACCESS_TOKEN.key}:{new_session_id}",
        token,
        ex=timedelta(minutes=settings.JWT_REDIS_EXPIRE_MINUTES),
    )
    await redis.sadd(
        f"{RedisInitKeyEnum.USER_SESSIONS.key}:{db_user.id}", new_session_id
    )
    old_device_info = await redis.get(
        f"{RedisInitKeyEnum.DEVICE_INFO.key}:{session_id}"
    )
    new_device_info = str(
        {
            "user_agent": request.headers.get("user-agent"),
            "login_ip": request.client.host,
            "user_id": db_user.id,
        }
    )
    if old_device_info != new_device_info:
        # 如果设备信息不一致，删除旧的设备信息
        # 这里可以提示用户 token 当前登录环境变了
        pass
    await redis.set(
        f"{RedisInitKeyEnum.DEVICE_INFO.key}:{new_session_id}",
        new_device_info,
        ex=7 * 24 * 60 * 60,
    )
    # 删除旧的device_info
    await redis.delete(f"{RedisInitKeyEnum.DEVICE_INFO.key}:{session_id}")
    # 删除旧的access_token
    await redis.delete(f"{RedisInitKeyEnum.ACCESS_TOKEN.key}:{session_id}")
    # 删除旧的refresh_token
    await redis.srem(f"{RedisInitKeyEnum.USER_SESSIONS.key}:{db_user.id}", session_id)
    await redis.delete(f"{RedisInitKeyEnum.REFRESH_TOKEN.key}:{session_id}")
    # 设置新的refresh_token
    await redis.set(
        f"{RedisInitKeyEnum.REFRESH_TOKEN.key}:{new_session_id}",
        f"{db_user.id}",
        ex=7 * 24 * 60 * 60,
    )
    response.set_cookie(
        key="session_id",
        value=new_session_id,
        httponly=True,
        # secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )
    return {
        "code": 200,
        "msg": "刷新成功",
        "data": TokenOut(access_token=token, token_type="bearer"),
    }


@auth_router.get(
    "/routers",
    summary="获取当前用户路由",
    response_model=ResponseModel[MenuRoutersOut],
)
async def get_router(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(AuthService.get_current_user),
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
    current_user: User = Depends(AuthService.get_current_user),
):
    """
    获取当前用户信息
    :return:
    """
    data = UserOut.model_validate(current_user).model_dump(exclude={"roles"})
    return Res.success(data=data)


@auth_router.get(
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
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"verify_exp": False},
    )
    session_id = payload.get("session_id", "")
    await AuthService.logout(redis=redis, session_id=session_id)
    logger.info(f"用户 {payload.get('username', '')} 退出成功")
    return Res.success(msg="退出成功")


@auth_router.get("/devices", summary="查看登录设备")
async def list_devices(
    user: User = Depends(AuthService.get_current_user),
    redis: aioredis.Redis = Depends(get_async_redis),
):
    session_ids = await redis.smembers(
        f"{RedisInitKeyEnum.USER_SESSIONS.key}:{user.id}"
    )
    devices = []

    for sid in session_ids:
        device_key = f"{RedisInitKeyEnum.DEVICE_INFO.key}:{sid}"
        device_info = await redis.get(device_key)
        if device_info:
            info = eval(device_info) if isinstance(device_info, str) else device_info
            devices.append(
                {
                    "session_id": sid,
                    "user_agent": info.get("user_agent"),
                    "login_ip": info.get("login_ip"),
                }
            )
        else:
            # 如果 device_info 没了，就清理掉这条无效 session
            await redis.srem(f"{RedisInitKeyEnum.USER_SESSIONS.key}:{user.id}", sid)

    return Res.success(data=devices, msg="设备列表获取成功")


@auth_router.get(
    "/request_info", summary="获取请求源信息", response_model=ResponseModel[dict]
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
