"""
@File: auth.py
@Author: GuaiMiu
@Date: 2025/3/19 15:28
@Version: 1.0
@Description:
"""

from collections import defaultdict
from datetime import timedelta, datetime, timezone
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jwt import InvalidTokenError
from redis import asyncio as aioredis
from sqlmodel.ext.asyncio.session import AsyncSession

from app.admin.dao.menu import menu_curd
from app.admin.dao.user import user_crud
from app.admin.models.menu import Menu
from app.admin.models.role import Role
from app.admin.models.user import User
from app.admin.schemas.auth import UserLoginIn, UserRegisterIn, TokenPayload
from app.core.config import settings
from app.core.database import get_async_redis, get_async_session
from app.core.exception import (
    LoginException,
    ServiceException,
    AuthException,
    PermissionException,
)
from app.enum.redis import RedisInitKeyEnum
from app.utils.logger import logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class AuthService:
    """
    认证服务类
    """

    @classmethod
    async def login(
        cls,
        request: Request,
        db: AsyncSession,
        redis: aioredis.Redis,
        login_user: UserLoginIn,
    ) -> User:
        """
        用户登录服务层
        :param request:
        :param redis:
        :param db:
        :param login_user:
        :return:
        """
        account_lock = await redis.get(
            f"{RedisInitKeyEnum.ACCOUNT_LOCK.key}:{login_user.username}"
        )
        if login_user.username == account_lock:
            raise LoginException(data="", msg=f"账号已锁定，请10分钟后再试")
        db_user = await user_crud.get_by_field(db, "username", login_user.username)
        # 用户不存在
        if not db_user:
            raise LoginException(msg=f"用户名或密码错误，请重新登录")
        # 用户被禁用
        if not db_user.status:
            raise LoginException(
                msg=f'用户 "{db_user.username}" 已被禁用，请联系管理员'
            )
        # 用户已删号跑路
        if db_user.is_deleted:
            raise LoginException(
                msg=f'用户 "{db_user.username}" 已删号跑路，请联系管理员'
            )
        # 密码错误
        if not db_user.verify_password(login_user.password):
            # 记录错误次数
            db_user.login_error_count += 1
            await user_crud.update(db, db_user)
            password_error_counted = (
                await redis.get(
                    f"{RedisInitKeyEnum.PASSWORD_ERROR_COUNT.key}:{login_user.username}"
                )
                or 0
            )
            password_error_count = int(password_error_counted) + 1
            await redis.set(
                f"{RedisInitKeyEnum.PASSWORD_ERROR_COUNT.key}:{login_user.username}",
                password_error_count,
                ex=timedelta(minutes=10),
            )
            if password_error_count > 5:
                await redis.delete(
                    f"{RedisInitKeyEnum.PASSWORD_ERROR_COUNT.key}:{login_user.username}"
                )
                await redis.set(
                    f"{RedisInitKeyEnum.ACCOUNT_LOCK.key}:{login_user.username}",
                    login_user.username,
                    ex=timedelta(minutes=10),
                )
                raise LoginException(
                    data="", msg="10分钟内密码错误超过5次，账号已锁定，请10分钟后再试"
                )
            raise LoginException(msg=f"用户名或密码错误，请重新登录")
        # 更新最后登录时间
        db_user.last_login_time = datetime.now()
        db_user.last_login_ip = request.client.host
        await user_crud.update(db, db_user)
        return db_user

    @classmethod
    async def register(
        cls,
        db: AsyncSession,
        user: UserRegisterIn,
    ) -> User:
        """
        用户注册服务层
        :param db:
        :param user:
        :return:
        """
        repeat_username = await user_crud.get_by_field(db, "username", user.username)
        repeat_mail = await user_crud.get_by_field(db, "mail", user.mail)
        if repeat_username:
            raise ServiceException(msg=f"用户名 {user.username} 已被注册")
        elif repeat_mail:
            raise ServiceException(msg=f"邮箱 {user.mail} 已被注册")
        user = User.model_validate(user)
        db_user = await user_crud.create(db, user)
        return db_user

    @classmethod
    async def create_access_token(
        cls,
        data: TokenPayload,
        expires_delta: timedelta | None = None,
    ) -> str:
        """
        创建访问令牌
        :param expires_delta:
        :param data:
        :return:
        """
        to_encode = data.model_dump().copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.JWT_EXPIRE_MINUTES
            )
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt

    @classmethod
    async def get_current_user_menus(
        cls,
        current_user: User,
        db: AsyncSession,
    ):
        """
        获取用户菜单
        :return:
        """
        menus = set()
        for role in current_user.roles:
            for menu in role.menus:
                if menu.status:
                    menus.add(menu)
        return list(menus)

    @classmethod
    async def get_current_user_routers(cls, db: AsyncSession, current_user: User):
        """

        :param db:
        :param current_user:
        :return:
        """
        if current_user.is_superuser:
            menus = await menu_curd.get_all_by_fields(
                db,
                {
                    "status": True,
                    "is_deleted": False,
                },
            )
        else:
            menus = await cls.get_current_user_menus(current_user, db)
        return await cls.__build_menu(menus, 0)

    @classmethod
    async def __build_menu(cls, all_menu: list[Menu], parent_perm_id):
        """

        :param all_menu:
        :param parent_perm_id:
        :return:
        """

        # 先对菜单按照 `sort` 进行全局排序，确保子菜单顺序正确
        all_menu.sort(key=lambda x: getattr(x, "sort", 0))

        menu_map = defaultdict(list)
        for menu in all_menu:
            if menu.type == 3:
                continue
            menu_map[menu.pid].append(menu)

        def recursive_build(pid):
            """递归构建菜单"""
            if pid not in menu_map:
                return []
            menu_list = []
            for menu in menu_map[pid]:
                dict_menu = menu.model_dump()
                dict_menu["children"] = recursive_build(menu.id)
                menu_list.append(dict_menu)
            return menu_list

        return recursive_build(parent_perm_id)

    @staticmethod
    def _normalize_token(value: str | bytes | None) -> str:
        if not value:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    @classmethod
    async def _get_user_from_token(
        cls,
        token: str,
        db: AsyncSession,
        redis: aioredis.Redis,
    ) -> User:
        if not token:
            raise AuthException(msg="请先登录")
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            redis_token = await redis.get(
                f"{RedisInitKeyEnum.ACCESS_TOKEN.key}:{payload.get('session_id')}"
            )
            redis_token = cls._normalize_token(redis_token)
            if not redis_token or redis_token != token:
                logger.warning(
                    f"用户 {payload.get('username', '未获取到USERNAME')} Token已失效"
                )
                raise AuthException(msg="Token已失效，请重新登录")
        except InvalidTokenError:
            logger.warning("Token异常，请重新登录")
            raise AuthException(msg="Token异常，请重新登录")
        user = await db.get(User, payload["id"])
        if not user:
            logger.warning("用户不存在，请重新登录")
            raise AuthException(msg="用户不存在，请重新登录")
        if user.is_deleted:
            logger.warning("用户已删除，请重新登录")
            raise AuthException(msg="用户已被删除，请重新登录")
        if not user.status:
            logger.warning("用户已被禁用，请重新登录")
            raise AuthException(msg="用户已被禁用，请重新登录")
        return user

    @classmethod
    async def get_current_user(
        cls,
        token: Annotated[str, Depends(oauth2_scheme)],
        db: AsyncSession = Depends(get_async_session),
        redis: aioredis.Redis = Depends(get_async_redis),
    ):
        """
        获取当前用户
        :param token:
        :param db:
        :param redis:
        :return:
        """
        return await cls._get_user_from_token(token, db, redis)

    @classmethod
    async def refresh_token(cls, refresh_token: str):
        """
        刷新令牌
        :param refresh_token:
        :return:
        """

        return refresh_token

    @classmethod
    async def logout(cls, session_id: str, redis: aioredis.Redis) -> bool:
        """
        登出
        :param session_id:
        :param redis:
        :return:
        """
        await redis.delete(f"{RedisInitKeyEnum.ACCESS_TOKEN.key}:{session_id}")
        await redis.delete(f"{RedisInitKeyEnum.REFRESH_TOKEN.key}:{session_id}")
        await redis.delete(f"{RedisInitKeyEnum.DEVICE_INFO.key}:{session_id}")

        return True

    @classmethod
    async def get_request_info(
        cls,
        request: Request,
    ) -> dict:
        """
        获取请求信息
        :param request:
        :return:
        """
        headers = request.headers
        return {
            "ip": headers.get("x-forwarded-for", request.client.host),
            "port": request.client.port,
            "user_agent": headers.get("user-agent", ""),
            "referer": headers.get("referer", ""),
            "host": headers.get("host", ""),
            "method": request.method,
            "url": str(request.url),
        }


async def get_user_roles(
    current_user: User = Depends(AuthService.get_current_user),
) -> list[Role]:
    """
    获取用户角色
    :return:
    """
    return current_user.roles


async def get_user_permissions(
    current_user: User = Depends(AuthService.get_current_user),
    current_roles: list[Role] = Depends(get_user_roles),
) -> list[str]:
    """
    获取用户权限
    :return:
    """
    if current_user.is_superuser:
        return ["*:*:*"]
    else:
        permissions = set()
        for role in current_roles:
            if not role.status:
                continue
            for permission in role.menus:
                if not permission.status and permission.type != 3:
                    continue
                if permission.permission_char:
                    permissions.add(permission.permission_char)
        return list(permissions)


async def check_user_permission(
    permissions: SecurityScopes,
    current_user: User = Depends(AuthService.get_current_user),
    user_permissions: list = Depends(get_user_permissions),
):
    """
    检查用户的的权限
    :return:
    """
    if current_user.is_superuser:
        return
        # 检查用户是否拥有所需的权限
    for scope in permissions.scopes:
        if scope not in user_permissions:
            raise PermissionException(msg="您无权访问此接口")
