"""
@File: setup.py
@Author: GuaiMiu
@Date: 2026/02/09
@Version: 1.0
@Description: 初次安装引导服务
"""

from __future__ import annotations

from pathlib import Path
import os
import secrets

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import text
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from redis import asyncio as aioredis

from app.core.config import settings
from app.core.database import reload_runtime
from app.core.exception import ServiceException
from app.modules.system.service.config import ConfigCenterService
from app.modules.system.services.install_state import InstallStateService
from app.modules.system.typed.keys import ConfigKey
from app.modules.system.typed.specs import get_default
from app.modules.admin.models.user import User


class SetupService:
    """
    系统安装引导服务。
    提供 .env 写入与首次配置持久化能力。
    """

    SETUP_ENV_MAP = {
        "app_name": "APP_NAME",
        "database_type": "DATABASE_TYPE",
        "database_host": "DATABASE_HOST",
        "database_port": "DATABASE_PORT",
        "database_user": "DATABASE_USER",
        "database_password": "DATABASE_PASSWORD",
        "database_name": "DATABASE_NAME",
        "database_url": "DATABASE_URL",
        "redis_enable": "REDIS_ENABLE",
        "redis_host": "REDIS_HOST",
        "redis_port": "REDIS_PORT",
        "redis_password": "REDIS_PASSWORD",
        "redis_db": "REDIS_DB",
        "storage_path": "DISK_ROOT",
        "jwt_secret_key": "JWT_SECRET_KEY",
    }

    SETUP_REGISTRY_KEY_MAP = {
        "app_name": ConfigKey.SYSTEM_SITE_NAME,
        "allow_register": ConfigKey.AUTH_ALLOW_REGISTER,
        "storage_path": ConfigKey.STORAGE_PATH,
        "database_type": ConfigKey.DATABASE_TYPE,
        "database_host": ConfigKey.DATABASE_HOST,
        "database_port": ConfigKey.DATABASE_PORT,
        "database_user": ConfigKey.DATABASE_USER,
        "database_name": ConfigKey.DATABASE_NAME,
        "database_url": ConfigKey.DATABASE_URL,
        "redis_enable": ConfigKey.REDIS_ENABLE,
        "redis_host": ConfigKey.REDIS_HOST,
        "redis_port": ConfigKey.REDIS_PORT,
        "redis_db": ConfigKey.REDIS_DB,
    }

    PROGRESS_TITLES = {
        "system": "系统检查",
        "database": "数据库初始化",
        "superuser": "管理员创建",
        "redis": "Redis 检查",
    }

    _progress: dict[str, dict[str, object]] = {}

    @classmethod
    def _default_for(cls, key: str, fallback: object = None) -> object:
        registry_key = cls.SETUP_REGISTRY_KEY_MAP.get(key)
        if not registry_key:
            return fallback
        return get_default(registry_key, fallback)

    @staticmethod
    def _as_bool(value: object, fallback: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "yes", "on"}:
                return True
            if lowered in {"0", "false", "no", "off"}:
                return False
        return fallback

    @staticmethod
    def _as_int(value: object, fallback: int) -> int:
        if value in (None, ""):
            return fallback
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _resolve_env_path() -> Path:
        candidates = [
            Path("/app/config/.env"),
            Path("/app/backend/.env"),
            Path.cwd() / ".env",
            Path.cwd() / "backend" / ".env",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[2]

    @classmethod
    def _reset_progress(cls) -> None:
        cls._progress = {
            key: {"status": "pending", "message": "等待开始", "skipped": False}
            for key in cls.PROGRESS_TITLES
        }

    @classmethod
    def _set_progress(
        cls,
        key: str,
        status: str,
        message: str,
        skipped: bool = False,
    ) -> None:
        if key not in cls._progress:
            cls._progress[key] = {"status": "pending", "message": "", "skipped": False}
        cls._progress[key].update(
            {"status": status, "message": message, "skipped": skipped}
        )

    @classmethod
    def get_progress(cls) -> dict[str, dict[str, object]]:
        if not cls._progress:
            cls._reset_progress()
        return cls._progress

    @classmethod
    def get_form_defaults(cls) -> dict[str, object]:
        merged = cls._resolve_setup_payload({})
        default_db_type = str(cls._default_for("database_type", "sqlite"))
        db_type = (merged.get("database_type") or default_db_type).strip().lower()
        database_url = merged.get("database_url") or cls._default_for(
            "database_url", "sqlite+aiosqlite:///./data.db"
        )
        return {
            "app_name": str(
                merged.get("app_name")
                or cls._default_for("app_name", settings.APP_NAME or "CowDisk")
            ),
            "database_type": db_type if db_type in {"sqlite", "mysql"} else "sqlite",
            "database_host": str(
                merged.get("database_host") or cls._default_for("database_host", "127.0.0.1")
            ),
            "database_port": cls._as_int(
                merged.get("database_port"), int(cls._default_for("database_port", 3306))
            ),
            "database_user": str(merged.get("database_user") or ""),
            "database_name": str(merged.get("database_name") or ""),
            "database_url": str(database_url),
            "superuser_name": str(settings.SUPERUSER_NAME or "admin"),
            "superuser_mail": str(settings.SUPERUSER_MAIL or "admin@example.com"),
            "allow_register": cls._as_bool(
                merged.get("allow_register"), bool(cls._default_for("allow_register", True))
            ),
            "redis_enable": cls._as_bool(
                merged.get("redis_enable"), bool(cls._default_for("redis_enable", False))
            ),
            "redis_host": str(
                merged.get("redis_host") or cls._default_for("redis_host", "127.0.0.1")
            ),
            "redis_port": cls._as_int(
                merged.get("redis_port"), int(cls._default_for("redis_port", 6379))
            ),
            "redis_db": cls._as_int(merged.get("redis_db"), int(cls._default_for("redis_db", 0))),
            "storage_path": str(merged.get("storage_path") or cls._default_for("storage_path", "/app/data")),
        }

    @classmethod
    def _resolve_setup_payload(cls, payload: dict) -> dict:
        """
        合并安装配置，优先级：表单提交 > 环境变量/.env > 默认值。
        """

        def _get_env_value(key: str):
            env_key = cls.SETUP_ENV_MAP.get(key)
            if env_key and env_key in os.environ:
                return os.environ.get(env_key)
            return getattr(settings, env_key, None) if env_key else None

        def _pick_value(key: str):
            payload_value = payload.get(key)
            if payload_value is not None and payload_value != "":
                return payload_value
            env_value = _get_env_value(key)
            if env_value is not None and env_value != "":
                return env_value
            return cls._default_for(key)

        resolved = dict(payload)
        for key in cls.SETUP_ENV_MAP:
            resolved[key] = _pick_value(key)
        return resolved

    @classmethod
    def _build_database_url(cls, payload: dict) -> str:
        """
        根据安装表单生成数据库连接 URL。
        """
        db_type = (payload.get("database_type") or "").strip().lower()
        if db_type == "sqlite":
            return payload.get("database_url") or str(
                cls._default_for("database_url", "sqlite+aiosqlite:///./data.db")
            )
        db_url = payload.get("database_url")
        if db_url:
            return db_url
        user = payload.get("database_user") or ""
        password = payload.get("database_password") or ""
        host = payload.get("database_host") or cls._default_for("database_host", "127.0.0.1")
        port = payload.get("database_port") or cls._default_for("database_port", 3306)
        name = payload.get("database_name") or ""
        return f"mysql+aiomysql://{user}:{password}@{host}:{port}/{name}"

    @classmethod
    def _apply_env_updates(
        cls,
        content: str,
        updates: dict[str, str],
        comment_out: set[str] | None = None,
        drop_keys: set[str] | None = None,
    ) -> str:
        """
        将配置更新写入 .env 内容。
        保留未匹配的原有注释和顺序。
        """
        lines = content.splitlines()
        seen = set()
        comment_out = comment_out or set()
        drop_keys = drop_keys or set()
        output: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                output.append(line)
                continue
            candidate = stripped
            if stripped.startswith("#"):
                candidate = stripped[1:].lstrip()
            if "=" not in candidate:
                output.append(line)
                continue
            key = candidate.split("=", 1)[0].strip()
            if key in drop_keys:
                continue
            if key in updates:
                value = updates[key]
                if key in comment_out:
                    output.append(f"#{key}={value}")
                else:
                    output.append(f"{key}={value}")
                seen.add(key)
                continue
            output.append(line)
        for key, value in updates.items():
            if key not in seen:
                if key in drop_keys:
                    continue
                if key in comment_out:
                    output.append(f"#{key}={value}")
                else:
                    output.append(f"{key}={value}")
        return "\n".join(output) + "\n"

    @classmethod
    def write_env(cls, payload: dict) -> Path:
        """
        写入 .env 文件，返回实际路径。
        """
        def _str_or_empty(value: object) -> str:
            if value is None:
                return ""
            return str(value)

        def _to_bool(value: object) -> bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return value != 0
            if isinstance(value, str):
                return value.strip().lower() in {"1", "true", "yes", "on"}
            return False

        env_path = cls._resolve_env_path()
        template_path = env_path if env_path.exists() else Path.cwd() / ".env.example"
        if template_path.exists():
            raw = template_path.read_text(encoding="utf-8")
        else:
            raw = ""
        database_type = payload.get("database_type") or ""
        database_url = payload.get("database_url") or ""
        if database_type.strip().lower() == "sqlite" and not database_url:
            database_url = "sqlite+aiosqlite:///./data.db"
        jwt_secret = payload.get("jwt_secret_key") or secrets.token_hex(32)
        redis_enable = _to_bool(payload.get("redis_enable"))
        updates = {
            "INSTALL_COMPLETED": "false",
            "DATABASE_TYPE": database_type,
            "DATABASE_HOST": payload.get("database_host") or "",
            "DATABASE_PORT": _str_or_empty(payload.get("database_port")),
            "DATABASE_USER": payload.get("database_user") or "",
            "DATABASE_PASSWORD": payload.get("database_password") or "",
            "DATABASE_NAME": payload.get("database_name") or "",
            "DATABASE_URL": database_url,
            "REDIS_ENABLE": "true" if redis_enable else "false",
            "REDIS_HOST": payload.get("redis_host") or "",
            "REDIS_PORT": _str_or_empty(payload.get("redis_port")),
            "REDIS_PASSWORD": payload.get("redis_password") or "",
            "REDIS_DB": _str_or_empty(payload.get("redis_db")),
            "JWT_SECRET_KEY": jwt_secret,
        }
        comment_out = set()
        if database_type.strip().lower() == "sqlite":
            comment_out.update(
                {
                    "DATABASE_HOST",
                    "DATABASE_PORT",
                    "DATABASE_USER",
                    "DATABASE_PASSWORD",
                    "DATABASE_NAME",
                }
            )
        if not redis_enable:
            comment_out.update(
                {
                    "REDIS_ENABLE",
                    "REDIS_HOST",
                    "REDIS_PORT",
                    "REDIS_PASSWORD",
                    "REDIS_DB",
                }
            )
        drop_keys = {
            "SUPERUSER_NAME",
            "SUPERUSER_PASSWORD",
            "SUPERUSER_MAIL",
            "APP_NAME",
            "APP_DESCRIPTION",
            "DISK_ROOT",
            "UPLOAD_MAX_SIZE",
            "PREVIEW_MAX_DURATION",
            "DOWNLOAD_TOKEN_TTL",
        }
        content = cls._apply_env_updates(raw, updates, comment_out, drop_keys)
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text(content, encoding="utf-8")
        return env_path

    @classmethod
    def write_install_completed(cls, completed: bool) -> Path:
        env_path = cls._resolve_env_path()
        raw = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
        updates = {"INSTALL_COMPLETED": "true" if completed else "false"}
        content = cls._apply_env_updates(raw, updates)
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text(content, encoding="utf-8")
        return env_path

    @classmethod
    async def bootstrap_database(cls, payload: dict) -> bool:
        """
        使用安装表单提供的配置初始化数据库。
        会创建所有表，并写入初始配置项。
        """
        # 确保模型被导入注册到 SQLModel.metadata
        from app.modules.admin.models.menu import Menu  # noqa: F401
        from app.modules.admin.models.role import Role, RoleMenuLink  # noqa: F401
        from app.modules.admin.models.user import User  # noqa: F401
        from app.modules.disk.models.file import File  # noqa: F401
        from app.modules.disk.models.share import Share  # noqa: F401
        from app.modules.disk.models.storage import Storage  # noqa: F401
        from app.audit.models import AuditLog  # noqa: F401

        database_url = cls._build_database_url(payload)
        engine = create_async_engine(
            database_url,
            future=True,
            connect_args={"check_same_thread": False}
            if database_url.startswith("sqlite+aiosqlite")
            else {},
        )
        async_session_local = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        try:
            async with engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)
        except Exception as exc:
            raise ServiceException(msg=f"创建表失败: {exc}") from exc
        async with async_session_local() as session:
            try:
                await cls._run_init_sql(session=session, database_url=database_url)
            except Exception as exc:
                raise ServiceException(msg=f"初始化 SQL 失败: {exc}") from exc
            try:
                await cls._seed_config(session=session, payload=payload)
            except ServiceException as exc:
                detail = (exc.msg or "").strip() or repr(exc)
                raise ServiceException(msg=f"初始化配置失败: {detail}") from exc
            except Exception as exc:
                detail = str(exc).strip() or repr(exc)
                raise ServiceException(msg=f"初始化配置失败: {detail}") from exc
            try:
                superuser_created = await cls._create_superuser(
                    session=session, payload=payload
                )
            except Exception as exc:
                raise ServiceException(msg=f"创建超级管理员失败: {exc}") from exc
        await engine.dispose()
        return superuser_created

    @classmethod
    async def _run_init_sql(cls, session: AsyncSession, database_url: str) -> None:
        """
        执行初始化 SQL 脚本（菜单/角色/权限）。
        """
        sql_path = Path(__file__).resolve().parents[3] / "sql" / "init.sql"
        if not sql_path.exists():
            return
        sql_script = sql_path.read_text(encoding="utf-8")
        is_sqlite = database_url.startswith("sqlite")
        if is_sqlite:
            sql_script = (
                sql_script.replace("`backend`.", "")
                .replace("INSERT INTO", "INSERT OR IGNORE INTO")
            )
        for statement in sql_script.split(";"):
            statement = statement.strip()
            if not statement:
                continue
            # Strip full-line comments before executing.
            lines = [
                line
                for line in statement.splitlines()
                if line.strip() and not line.lstrip().startswith("--")
            ]
            cleaned = "\n".join(lines).strip()
            if not cleaned:
                continue
            await session.execute(text(cleaned))
        await session.commit()

    @classmethod
    async def ensure_rbac_seed(cls, session: AsyncSession) -> None:
        """
        幂等补齐后台菜单/角色/权限种子数据。
        用于安装后或异常数据修复场景。
        """
        database_url = settings.DATABASE_URL or ""
        if not database_url:
            db_type = (settings.DATABASE_TYPE or "").strip().lower()
            if db_type == "sqlite":
                database_url = "sqlite+aiosqlite:///./data.db"
            else:
                user = settings.DATABASE_USER or ""
                password = settings.DATABASE_PASSWORD or ""
                host = settings.DATABASE_HOST or "127.0.0.1"
                port = settings.DATABASE_PORT or 3306
                name = settings.DATABASE_NAME or ""
                database_url = (
                    f"mysql+aiomysql://{user}:{password}@{host}:{port}/{name}"
                )
        await cls._run_init_sql(session=session, database_url=database_url)

    @classmethod
    async def _seed_config(cls, session: AsyncSession, payload: dict):
        """
        写入初始动态配置。
        """
        app_name = payload.get("app_name")
        storage_path = payload.get("storage_path")
        allow_register = payload.get("allow_register")
        overrides: dict[str, object] = {}
        if app_name not in (None, ""):
            overrides[ConfigKey.SYSTEM_SITE_NAME] = app_name
        if storage_path not in (None, ""):
            overrides[ConfigKey.STORAGE_PATH] = storage_path
        if allow_register is not None:
            overrides[ConfigKey.AUTH_ALLOW_REGISTER] = allow_register
        await ConfigCenterService(session).ensure_defaults(overrides=overrides)
        await session.commit()
        ConfigCenterService.clear_cache()

    @classmethod
    async def _create_superuser(cls, session: AsyncSession, payload: dict) -> bool:
        """
        在安装阶段创建超级管理员用户。
        """
        existing = (await session.exec(select(User))).first()
        if existing:
            return False
        username = (payload.get("superuser_name") or "").strip()
        password = (payload.get("superuser_password") or "").strip()
        mail = (payload.get("superuser_mail") or "").strip()
        if not username or not password or not mail:
            raise ServiceException(msg="超级管理员信息不完整")
        default_quota_gb = int(get_default(ConfigKey.AUTH_DEFAULT_USER_QUOTA_GB, 10))
        total_space = max(int(default_quota_gb), 0) * 1024 * 1024 * 1024
        user = User(
            username=username,
            password=User.create_password(password),
            nickname="管理员",
            mail=mail,
            is_superuser=True,
            total_space=total_space,
        )
        session.add(user)
        await session.commit()
        return True

    @classmethod
    def _check_system(cls, payload: dict, env_path: Path) -> tuple[bool, str]:
        storage_path = payload.get("storage_path") or ""
        if not env_path.exists():
            return False, ".env 写入失败"
        if not storage_path:
            return False, "未设置存储路径"
        return True, "环境检查通过"

    @classmethod
    async def _check_redis(cls, payload: dict) -> tuple[bool, str, bool]:
        if not payload.get("redis_enable"):
            return True, "Redis 未启用，已跳过检查", True
        host = payload.get("redis_host") or cls._default_for("redis_host", "127.0.0.1")
        port = payload.get("redis_port") or cls._default_for("redis_port", 6379)
        db = payload.get("redis_db") or cls._default_for("redis_db", 0)
        password = payload.get("redis_password") or None
        client = aioredis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
        )
        try:
            await client.ping()
            return True, "Redis 连接正常", False
        except Exception as exc:
            return False, f"Redis 连接失败: {exc}", False
        finally:
            await client.close()

    @classmethod
    async def run_setup(cls, payload: dict) -> dict:
        """
        执行首次安装流程。
        包括写入 .env 与初始化数据库。
        """
        cls._reset_progress()
        InstallStateService.mark_phase("RUNNING", "安装流程启动")
        merged_payload = cls._resolve_setup_payload(payload)
        if not merged_payload.get("database_type"):
            InstallStateService.mark_phase("FAILED", "数据库类型不能为空")
            raise ServiceException(msg="数据库类型不能为空")
        cls._set_progress("system", "running", "写入 .env 配置")
        env_path = cls.write_env(merged_payload)
        system_ok, system_message = cls._check_system(merged_payload, env_path)
        cls._set_progress(
            "system",
            "success" if system_ok else "failed",
            system_message,
        )
        cls._set_progress("database", "running", "初始化数据库")
        try:
            superuser_created = await cls.bootstrap_database(merged_payload)
            database_ok = True
            database_message = "数据库初始化完成"
            cls._set_progress("database", "success", database_message)
        except ServiceException as exc:
            detail = (exc.msg or "").strip() or repr(exc)
            InstallStateService.mark_phase("FAILED", f"数据库初始化失败: {detail}")
            cls._set_progress("database", "failed", f"数据库初始化失败: {detail}")
            raise ServiceException(msg=f"数据库初始化失败: {detail}") from exc
        except Exception as exc:
            detail = str(exc).strip() or repr(exc)
            InstallStateService.mark_phase("FAILED", f"数据库初始化失败: {detail}")
            cls._set_progress("database", "failed", f"数据库初始化失败: {detail}")
            raise ServiceException(msg=f"数据库初始化失败: {detail}") from exc
        await reload_runtime()
        superuser_message = "超级管理员已创建" if superuser_created else "超级管理员已存在"
        cls._set_progress("superuser", "success", superuser_message)
        cls._set_progress("redis", "running", "检查 Redis 连接")
        redis_ok, redis_message, redis_skipped = await cls._check_redis(merged_payload)
        if redis_skipped:
            cls._set_progress("redis", "skipped", redis_message, True)
        else:
            cls._set_progress(
                "redis",
                "success" if redis_ok else "failed",
                redis_message,
            )
        cls.write_install_completed(True)
        await reload_runtime()
        InstallStateService.mark_done("安装流程已完成")
        return {
            "env_path": str(env_path),
            "system": {
                "ok": system_ok,
                "message": system_message,
                "skipped": False,
            },
            "database": {
                "ok": database_ok,
                "message": database_message,
                "skipped": False,
            },
            "superuser": {
                "ok": True,
                "message": superuser_message,
                "skipped": False,
            },
            "redis": {
                "ok": redis_ok,
                "message": redis_message,
                "skipped": redis_skipped,
            },
        }
