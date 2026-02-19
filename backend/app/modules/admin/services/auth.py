"""
@File: auth.py
@Author: GuaiMiu
@Date: 2025/3/19 15:28
@Version: 1.0
@Description:
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import secrets
import uuid
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jwt import InvalidTokenError
from redis import asyncio as aioredis
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.audit.decorator import audited
from app.core.config import settings
from app.core.database import get_async_redis, get_async_session
from app.core.exception import (
    AuthException,
    LoginException,
    PermissionException,
    ServiceException,
)
from app.enum.redis import RedisInitKeyEnum
from app.modules.admin.dao.menu import menu_curd
from app.modules.admin.dao.user import user_crud
from app.modules.admin.models.menu import Menu
from app.modules.admin.models.role import Role
from app.modules.admin.models.user import User, default_total_space_bytes
from app.modules.admin.schemas.auth import TokenPayload, UserLoginIn, UserRegisterIn
from app.modules.system.typed.config import Config
from app.shared.permission_match import has_permission
from app.utils.logger import logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def _extract_login(*_args, **_kwargs):
    result = _kwargs.get("result")
    login_user = _kwargs.get("login_user")
    user_id = _kwargs.get("user_id")
    if result:
        return {
            "resource_id": str(result.id),
            "resource_type": "USER",
            "detail": {"username": result.username},
            "user_id": result.id,
        }
    if login_user:
        return {"detail": {"username": login_user.username}}
    if user_id:
        return {"resource_id": str(user_id), "resource_type": "USER", "user_id": user_id}
    return {}


class AuthService:
    """
    认证服务类
    """

    SESSION_TTL_SECONDS = 7 * 24 * 60 * 60

    @classmethod
    def _access_token_key(cls, session_id: str) -> str:
        return f"{RedisInitKeyEnum.ACCESS_TOKEN.key}:{session_id}"

    @classmethod
    def _refresh_token_key(cls, session_id: str) -> str:
        return f"{RedisInitKeyEnum.REFRESH_TOKEN.key}:{session_id}"

    @classmethod
    def _device_info_key(cls, session_id: str) -> str:
        return f"{RedisInitKeyEnum.DEVICE_INFO.key}:{session_id}"

    @classmethod
    def _user_sessions_key(cls, user_id: int) -> str:
        return f"{RedisInitKeyEnum.USER_SESSIONS.key}:{user_id}"

    @classmethod
    def _session_meta_key(cls, session_id: str) -> str:
        return f"{RedisInitKeyEnum.SESSION_META.key}:{session_id}"

    @classmethod
    def _rate_limit_key(cls, action: str, identifier: str) -> str:
        return f"{RedisInitKeyEnum.AUTH_RATE_LIMIT.key}:{action}:{identifier}"

    @classmethod
    def _refresh_rotate_key(cls, user_id: int) -> str:
        return f"{RedisInitKeyEnum.REFRESH_ROTATE.key}:{user_id}"

    @staticmethod
    def _hash_refresh_token(refresh_token: str) -> str:
        return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_token(value: str | bytes | None) -> str:
        if not value:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    @classmethod
    def build_device_fingerprint(
        cls,
        *,
        user_agent: str | None,
        login_ip: str | None,
    ) -> str:
        base = f"{(user_agent or '').strip()}|{(login_ip or '').strip()}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    @classmethod
    async def apply_rate_limit(
        cls,
        redis: aioredis.Redis,
        *,
        action: str,
        identifier: str,
        limit: int,
        window_seconds: int,
    ) -> bool:
        key = cls._rate_limit_key(action, identifier or "unknown")
        current_raw = await redis.get(key)
        current = int(cls._normalize_token(current_raw) or "0") + 1
        ttl = await redis.ttl(key) if hasattr(redis, "ttl") else -1
        if ttl and ttl > 0:
            await redis.set(key, str(current), ex=ttl)
        else:
            await redis.set(key, str(current), ex=window_seconds)
        return current <= max(limit, 1)

    @classmethod
    async def apply_refresh_rotate_limit(
        cls,
        redis: aioredis.Redis,
        *,
        user_id: int,
    ) -> bool:
        key = cls._refresh_rotate_key(user_id)
        current_raw = await redis.get(key)
        current = int(cls._normalize_token(current_raw) or "0") + 1
        ttl = await redis.ttl(key) if hasattr(redis, "ttl") else -1
        if ttl and ttl > 0:
            await redis.set(key, str(current), ex=ttl)
        else:
            await redis.set(key, str(current), ex=24 * 60 * 60)
        return current <= max(settings.JWT_REFRESH_ROTATE_LIMIT, 1)

    @classmethod
    async def bind_session(
        cls,
        redis: aioredis.Redis,
        *,
        user_id: int,
        session_id: str,
        access_token: str,
        refresh_token: str,
        user_agent: str | None,
        login_ip: str | None,
    ) -> None:
        fingerprint = cls.build_device_fingerprint(
            user_agent=user_agent,
            login_ip=login_ip,
        )
        await redis.set(
            cls._access_token_key(session_id),
            access_token,
            ex=timedelta(minutes=settings.JWT_REDIS_EXPIRE_MINUTES),
        )
        await redis.set(
            cls._refresh_token_key(session_id),
            json.dumps(
                {
                    "user_id": user_id,
                    "token_hash": cls._hash_refresh_token(refresh_token),
                },
                ensure_ascii=False,
            ),
            ex=cls.SESSION_TTL_SECONDS,
        )
        await redis.set(
            cls._device_info_key(session_id),
            json.dumps(
                {
                    "user_agent": user_agent,
                    "login_ip": login_ip,
                    "user_id": user_id,
                },
                ensure_ascii=False,
            ),
            ex=cls.SESSION_TTL_SECONDS,
        )
        await redis.set(
            cls._session_meta_key(session_id),
            json.dumps(
                {
                    "fingerprint": fingerprint,
                    "user_id": user_id,
                },
                ensure_ascii=False,
            ),
            ex=cls.SESSION_TTL_SECONDS,
        )
        await redis.sadd(cls._user_sessions_key(user_id), session_id)

    @classmethod
    async def purge_session(
        cls,
        redis: aioredis.Redis,
        *,
        session_id: str,
        user_id: int | None = None,
    ) -> None:
        await redis.delete(cls._access_token_key(session_id))
        await redis.delete(cls._refresh_token_key(session_id))
        await redis.delete(cls._device_info_key(session_id))
        await redis.delete(cls._session_meta_key(session_id))
        if user_id is not None:
            await redis.srem(cls._user_sessions_key(user_id), session_id)

    @classmethod
    async def get_refresh_user_id(
        cls,
        redis: aioredis.Redis,
        *,
        session_id: str,
        refresh_token: str,
    ) -> int | None:
        if not refresh_token:
            return None
        raw = await redis.get(cls._refresh_token_key(session_id))
        if raw is None:
            return None
        value = cls._normalize_token(raw)
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        user_id = payload.get("user_id")
        expected_hash = str(payload.get("token_hash") or "")
        if not isinstance(user_id, int):
            return None
        actual_hash = cls._hash_refresh_token(refresh_token)
        if not expected_hash or not hmac.compare_digest(expected_hash, actual_hash):
            return None
        return user_id

    @classmethod
    def create_refresh_token(cls) -> str:
        return secrets.token_urlsafe(48)

    @classmethod
    async def validate_session_fingerprint(
        cls,
        redis: aioredis.Redis,
        *,
        session_id: str,
        user_agent: str | None,
        login_ip: str | None,
    ) -> bool:
        raw = await redis.get(cls._session_meta_key(session_id))
        if not raw:
            return False
        try:
            meta = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            return False
        if not isinstance(meta, dict):
            return False
        expected = str(meta.get("fingerprint") or "")
        current = cls.build_device_fingerprint(user_agent=user_agent, login_ip=login_ip)
        return bool(expected and expected == current)

    @classmethod
    def decode_access_token(
        cls,
        token: str,
        *,
        verify_exp: bool = True,
    ) -> dict:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
            leeway=30,
            options={"verify_exp": verify_exp},
        )

    @classmethod
    async def create_access_token(
        cls,
        data: TokenPayload,
        expires_delta: timedelta | None = None,
    ) -> str:
        to_encode = data.model_dump().copy()
        now = datetime.now(timezone.utc)
        expire = now + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
        to_encode.update(
            {
                "exp": expire,
                "iat": now,
                "nbf": now,
                "jti": uuid.uuid4().hex,
                "iss": settings.JWT_ISSUER,
                "aud": settings.JWT_AUDIENCE,
            }
        )
        return jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    @classmethod
    @audited(
        "LOGIN",
        resource_type="USER",
        extractors=[_extract_login],
        auto_commit=True,
    )
    async def login(
        cls,
        db: AsyncSession,
        redis: aioredis.Redis,
        login_user: UserLoginIn,
        client_ip: str | None = None,
        commit: bool = True,
    ) -> User:
        account_lock = await redis.get(
            f"{RedisInitKeyEnum.ACCOUNT_LOCK.key}:{login_user.username}"
        )
        if login_user.username == account_lock:
            raise LoginException(data="", msg="账号已锁定，请10分钟后再试")
        db_user = await user_crud.get_by_field(db, "username", login_user.username)
        if not db_user:
            raise LoginException(msg="用户名或密码错误，请重新登录")
        if not db_user.status:
            raise LoginException(msg=f'用户 "{db_user.username}" 已被禁用，请联系管理员')
        if db_user.is_deleted:
            raise LoginException(msg=f'用户 "{db_user.username}" 已删号跑路，请联系管理员')
        if not db_user.verify_password(login_user.password):
            db_user.login_error_count += 1
            await user_crud.update(db, db_user, commit=True)
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
                raise LoginException(data="", msg="10分钟内密码错误超过5次，账号已锁定，请10分钟后再试")
            raise LoginException(msg="用户名或密码错误，请重新登录")
        db_user.last_login_time = datetime.now()
        db_user.last_login_ip = client_ip or ""
        await user_crud.update(db, db_user, commit=commit)
        return db_user

    @classmethod
    async def register(
        cls,
        db: AsyncSession,
        user: UserRegisterIn,
        config: Config,
    ) -> User:
        allow_register = await config.auth.allow_register()
        if not allow_register:
            raise ServiceException(msg="当前已关闭注册，请联系管理员")
        repeat_username = await user_crud.get_by_field(db, "username", user.username)
        repeat_mail = await user_crud.get_by_field(db, "mail", user.mail)
        if repeat_username:
            raise ServiceException(msg=f"用户名 {user.username} 已被注册")
        if repeat_mail:
            raise ServiceException(msg=f"邮箱 {user.mail} 已被注册")
        user_model = User.model_validate(user)
        quota_gb = await config.auth.default_user_quota_gb()
        if quota_gb is not None and str(quota_gb) != "":
            try:
                user_model.total_space = max(int(quota_gb), 0) * 1024 * 1024 * 1024
            except (TypeError, ValueError):
                user_model.total_space = default_total_space_bytes()
        else:
            user_model.total_space = default_total_space_bytes()
        default_role = (
            await db.exec(
                select(Role).where(
                    Role.name == "普通用户",
                    Role.status == True,
                    Role.is_deleted == False,
                )
            )
        ).first()
        if default_role:
            user_model.roles = [default_role]
        return await user_crud.create(db, user_model)

    @classmethod
    async def get_current_user_menus(cls, current_user: User, db: AsyncSession):
        menus = set()
        for role in current_user.roles:
            for menu in role.menus:
                if menu.status:
                    menus.add(menu)
        return list(menus)

    @classmethod
    async def get_current_user_routers(cls, db: AsyncSession, current_user: User):
        if current_user.is_superuser:
            menus = await menu_curd.get_all_by_fields(
                db,
                {"status": True, "is_deleted": False},
            )
        else:
            menus = await cls.get_current_user_menus(current_user, db)
        return await cls.__build_menu(menus, 0)

    @classmethod
    async def __build_menu(cls, all_menu: list[Menu], parent_perm_id):
        all_menu.sort(key=lambda x: getattr(x, "sort", 0))
        menu_map = defaultdict(list)
        known_ids = {menu.id for menu in all_menu if menu.id is not None}
        for menu in all_menu:
            if menu.type == 3:
                continue
            pid = menu.pid
            if pid not in (0, None) and pid not in known_ids:
                pid = 0
            menu_map[pid].append(menu)

        def recursive_build(pid):
            if pid not in menu_map:
                return []
            menu_list = []
            for menu in menu_map[pid]:
                dict_menu = menu.model_dump()
                dict_menu["children"] = recursive_build(menu.id)
                menu_list.append(dict_menu)
            return menu_list

        return recursive_build(parent_perm_id)

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
            payload = cls.decode_access_token(token, verify_exp=True)
            redis_token = await redis.get(cls._access_token_key(payload.get("session_id", "")))
            redis_token = cls._normalize_token(redis_token)
            if not redis_token or redis_token != token:
                logger.warning("用户 %s Token已失效", payload.get("username", "unknown"))
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
        return await cls._get_user_from_token(token, db, redis)

    @classmethod
    @audited(
        "LOGOUT",
        resource_type="USER",
        extractors=[_extract_login],
        auto_commit=True,
    )
    async def logout(
        cls,
        session_id: str,
        redis: aioredis.Redis,
        user_id: int | None = None,
        commit: bool = False,
    ) -> bool:
        await cls.purge_session(redis, session_id=session_id, user_id=user_id)
        return True

    @classmethod
    async def get_request_info(cls, request: Request) -> dict:
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
    return current_user.roles


async def get_user_permissions(
    current_user: User = Depends(AuthService.get_current_user),
    current_roles: list[Role] = Depends(get_user_roles),
) -> list[str]:
    if current_user.is_superuser:
        return ["*:*:*"]
    permissions = set()
    for role in current_roles:
        if not role.status:
            continue
        for permission in role.menus:
            if not permission.permission_char:
                continue
            if not permission.status and permission.type != 3:
                continue
            if permission.is_deleted:
                continue
            permissions.add(permission.permission_char)
    return list(permissions)


async def check_user_permission(
    permissions: SecurityScopes,
    current_user: User = Depends(AuthService.get_current_user),
    user_permissions: list = Depends(get_user_permissions),
):
    if current_user.is_superuser:
        return
    for scope in permissions.scopes:
        if not has_permission(user_permissions, scope):
            raise PermissionException(msg="您无权访问此接口")
