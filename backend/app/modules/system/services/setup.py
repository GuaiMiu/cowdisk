"""
@File: setup.py
@Author: GuaiMiu
@Date: 2026/02/09
@Version: 1.0
@Description: 初次安装引导服务
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import secrets
from typing import Callable, NoReturn

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import text
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from redis import asyncio as aioredis

from app.core.config import settings
from app.core.database import reload_runtime
from app.core.exception import ServiceException
from app.modules.system.services.config import ConfigCenterService
from app.modules.system.services.install_state import InstallStateService
from app.modules.system.services.setup_fields import (
    SETUP_DEFAULTS,
    SETUP_FIELDS,
    get_setup_defaults,
)
from app.modules.system.typed.keys import ConfigKey
from app.modules.system.typed.specs import get_default
from app.modules.admin.models.user import User


@dataclass(frozen=True)
class _RollbackSnapshot:
    env_path: Path
    env_before: str | None
    sqlite_db_path: Path | None
    sqlite_db_existed: bool
    storage_path: Path | None
    storage_existed: bool


class SetupService:
    """
    系统安装引导服务。
    提供 .env 写入与首次配置持久化能力。
    """

    PROGRESS_TITLES = {
        "system": "系统检查",
        "database": "数据库初始化",
        "superuser": "管理员创建",
        "redis": "Redis 检查",
    }
    VALID_DATABASE_TYPES = {"sqlite", "mysql"}
    VALID_REDIS_AUTH_MODES = {"none", "password", "username_password"}
    DEFAULT_DATABASE_URL = str(SETUP_DEFAULTS["database_url"])

    _progress: dict[str, dict[str, object]] = {}

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
    def _as_str(value: object) -> str:
        return "" if value is None else str(value)

    @staticmethod
    def _normalize_database_url(value: object) -> str:
        return str(value or "").strip()

    @staticmethod
    def _infer_database_type_from_url(database_url: str) -> str:
        if database_url.startswith("sqlite+aiosqlite://"):
            return "sqlite"
        if database_url.startswith("mysql+aiomysql://"):
            return "mysql"
        return ""

    @staticmethod
    def _resolve_env_path() -> Path:
        backend_root = Path.cwd() / "backend"
        if backend_root.is_dir():
            return backend_root / ".env"
        return Path.cwd() / ".env"

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

    @staticmethod
    def _build_check(ok: bool, message: str, skipped: bool = False) -> dict[str, object]:
        return {
            "ok": ok,
            "message": message,
            "skipped": skipped,
        }

    @staticmethod
    def _error_detail(exc: Exception) -> str:
        if isinstance(exc, ServiceException):
            return (exc.msg or "").strip() or repr(exc)
        return str(exc).strip() or repr(exc)

    @classmethod
    def _fail_setup(
        cls,
        step: str | None,
        message: str,
        cleanup: Callable[[], None] | None = None,
    ) -> NoReturn:
        if step:
            cls._set_progress(step, "failed", message)
        InstallStateService.mark_failed(message)
        if cleanup is not None:
            try:
                cleanup()
            except Exception:
                # 回滚失败不应覆盖主错误语义。
                pass
        raise ServiceException(msg=message)

    @classmethod
    def _infer_redis_auth_mode(cls, payload: dict) -> str:
        mode = str(payload.get("redis_auth_mode") or "").strip().lower()
        if mode in cls.VALID_REDIS_AUTH_MODES:
            return mode
        has_username = bool(str(payload.get("redis_username") or "").strip())
        has_password = bool(str(payload.get("redis_password") or "").strip())
        if has_username and has_password:
            return "username_password"
        if has_password:
            return "password"
        return "none"

    @classmethod
    def _normalize_redis_auth_payload(cls, payload: dict) -> dict:
        normalized = dict(payload)
        if not cls._as_bool(normalized.get("redis_enable"), False):
            normalized["redis_username"] = ""
            normalized["redis_password"] = ""
            normalized["redis_auth_mode"] = "none"
            return normalized
        mode = cls._infer_redis_auth_mode(normalized)
        normalized["redis_auth_mode"] = mode
        if mode == "none":
            normalized["redis_username"] = ""
            normalized["redis_password"] = ""
        elif mode == "password":
            normalized["redis_username"] = ""
        return normalized

    @classmethod
    def _validate_setup_payload(cls, payload: dict) -> str | None:
        database_url = cls._normalize_database_url(payload.get("database_url"))
        if not database_url:
            return "数据库连接 URL 不能为空"
        db_type = cls._infer_database_type_from_url(database_url)
        if db_type not in cls.VALID_DATABASE_TYPES:
            return "数据库连接 URL 仅支持 sqlite+aiosqlite 或 mysql+aiomysql"
        if cls._as_bool(payload.get("redis_enable"), False):
            mode = cls._infer_redis_auth_mode(payload)
            password = str(payload.get("redis_password") or "").strip()
            username = str(payload.get("redis_username") or "").strip()
            if mode == "password" and not password:
                return "Redis 认证方式为仅密码时必须填写密码"
            if mode == "username_password":
                if not username:
                    return "Redis 认证方式为用户名+密码时必须填写用户名"
                if not password:
                    return "Redis 认证方式为用户名+密码时必须填写密码"
        return None

    @classmethod
    def _resolve_sqlite_db_path(cls, payload: dict) -> Path | None:
        database_url = cls._build_database_url(payload)
        db_type = cls._infer_database_type_from_url(database_url)
        if db_type != "sqlite":
            return None
        prefix = "sqlite+aiosqlite:///"
        if not database_url.startswith(prefix):
            return None
        raw = database_url[len(prefix) :].split("?", 1)[0].strip()
        if not raw:
            return None
        candidate = Path(raw)
        if candidate.is_absolute():
            return candidate
        return (Path.cwd() / candidate).resolve()

    @classmethod
    def _build_rollback_snapshot(cls, payload: dict) -> _RollbackSnapshot:
        env_path = cls._resolve_env_path()
        env_before = env_path.read_text(encoding="utf-8") if env_path.exists() else None
        sqlite_db_path = cls._resolve_sqlite_db_path(payload)
        sqlite_db_existed = sqlite_db_path.exists() if sqlite_db_path else True
        storage_path_value = str(payload.get("storage_path") or "").strip()
        storage_path = Path(storage_path_value).resolve() if storage_path_value else None
        storage_existed = storage_path.exists() if storage_path else True
        return _RollbackSnapshot(
            env_path=env_path,
            env_before=env_before,
            sqlite_db_path=sqlite_db_path,
            sqlite_db_existed=sqlite_db_existed,
            storage_path=storage_path,
            storage_existed=storage_existed,
        )

    @classmethod
    def _build_rollback_handler(
        cls, snapshot: _RollbackSnapshot
    ) -> Callable[[], None]:
        def _rollback() -> None:
            if snapshot.env_before is None:
                if snapshot.env_path.exists():
                    snapshot.env_path.unlink()
            else:
                snapshot.env_path.parent.mkdir(parents=True, exist_ok=True)
                snapshot.env_path.write_text(snapshot.env_before, encoding="utf-8")

            if snapshot.sqlite_db_path and not snapshot.sqlite_db_existed:
                for suffix in ("", "-wal", "-shm", "-journal"):
                    candidate = Path(f"{snapshot.sqlite_db_path}{suffix}")
                    if candidate.exists() and candidate.is_file():
                        candidate.unlink()

            if (
                snapshot.storage_path
                and not snapshot.storage_existed
                and snapshot.storage_path.exists()
            ):
                try:
                    snapshot.storage_path.rmdir()
                except OSError:
                    # 若目录已产生业务文件，不做激进删除，避免误删。
                    pass

        return _rollback

    @classmethod
    async def _finalize_setup_success(
        cls, cleanup: Callable[[], None] | None = None
    ) -> None:
        try:
            await reload_runtime()
            InstallStateService.mark_done("安装流程已完成")
        except Exception as exc:
            detail = cls._error_detail(exc)
            cls._fail_setup(None, f"安装收尾失败: {detail}", cleanup=cleanup)

    @classmethod
    def get_form_defaults(cls) -> dict[str, object]:
        merged = cls._resolve_setup_payload({})
        redis_username = cls._as_str(merged.get("redis_username"))
        redis_auth_mode = cls._infer_redis_auth_mode(merged)
        return {
            "app_name": str(merged.get("app_name") or ""),
            "database_url": cls._normalize_database_url(merged.get("database_url")),
            "superuser_name": str(merged.get("superuser_name") or ""),
            "superuser_mail": str(merged.get("superuser_mail") or ""),
            "allow_register": cls._as_bool(merged.get("allow_register"), True),
            "redis_enable": cls._as_bool(merged.get("redis_enable"), False),
            "redis_host": str(merged.get("redis_host") or ""),
            "redis_port": cls._as_int(merged.get("redis_port"), 6379),
            "redis_auth_mode": redis_auth_mode,
            "redis_username": redis_username,
            "redis_db": cls._as_int(merged.get("redis_db"), 0),
            "storage_path": str(merged.get("storage_path") or ""),
        }

    @classmethod
    def _resolve_setup_payload(cls, payload: dict) -> dict:
        """
        合并安装配置，优先级：表单提交 > 安装默认值。
        """
        resolved = get_setup_defaults()
        for field in SETUP_FIELDS:
            payload_value = payload.get(field)
            if payload_value is not None and payload_value != "":
                resolved[field] = payload_value
        resolved["database_url"] = cls._normalize_database_url(resolved.get("database_url"))
        return resolved

    @classmethod
    def _build_database_url(cls, payload: dict) -> str:
        return cls._normalize_database_url(payload.get("database_url"))

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
        env_path = cls._resolve_env_path()
        template_path = env_path if env_path.exists() else Path.cwd() / ".env.example"
        if template_path.exists():
            raw = template_path.read_text(encoding="utf-8")
        else:
            raw = ""
        database_url = cls._build_database_url(payload)
        database_type = cls._infer_database_type_from_url(database_url)
        jwt_secret = settings.JWT_SECRET_KEY or secrets.token_hex(32)
        redis_enable = cls._as_bool(payload.get("redis_enable"))
        updates = {
            "DATABASE_TYPE": database_type,
            "DATABASE_URL": database_url,
            "REDIS_ENABLE": "true" if redis_enable else "false",
            "REDIS_HOST": payload.get("redis_host") or "",
            "REDIS_PORT": cls._as_str(payload.get("redis_port")),
            "REDIS_USERNAME": payload.get("redis_username") or "",
            "REDIS_PASSWORD": payload.get("redis_password") or "",
            "REDIS_DB": cls._as_str(payload.get("redis_db")),
            "JWT_SECRET_KEY": jwt_secret,
        }
        comment_out = set()
        if not redis_enable:
            comment_out.update(
                {
                    "REDIS_ENABLE",
                    "REDIS_HOST",
                    "REDIS_PORT",
                    "REDIS_USERNAME",
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
            "DATABASE_HOST",
            "DATABASE_PORT",
            "DATABASE_USER",
            "DATABASE_PASSWORD",
            "DATABASE_NAME",
            "UPLOAD_MAX_SIZE",
            "PREVIEW_MAX_DURATION",
            "DOWNLOAD_TOKEN_TTL",
        }
        content = cls._apply_env_updates(raw, updates, comment_out, drop_keys)
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
                database_url = cls.DEFAULT_DATABASE_URL
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
        storage_dir = Path(str(storage_path))
        try:
            storage_dir.mkdir(parents=True, exist_ok=True)
            probe = storage_dir / f".setup_write_probe_{secrets.token_hex(6)}"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except Exception as exc:
            return False, f"存储路径不可写: {exc}"
        return True, "环境检查通过"

    @classmethod
    async def _check_redis(cls, payload: dict) -> tuple[bool, str, bool]:
        if not payload.get("redis_enable"):
            return True, "Redis 未启用，已跳过检查", True
        host = payload.get("redis_host") or SETUP_DEFAULTS["redis_host"]
        port = payload.get("redis_port") or SETUP_DEFAULTS["redis_port"]
        db = payload.get("redis_db") or SETUP_DEFAULTS["redis_db"]
        username = payload.get("redis_username") or None
        password = payload.get("redis_password") or None
        client = aioredis.Redis(
            host=host,
            port=port,
            db=db,
            username=username,
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
        InstallStateService.mark_running("安装流程启动")

        merged_payload = cls._normalize_redis_auth_payload(cls._resolve_setup_payload(payload))
        rollback = cls._build_rollback_handler(cls._build_rollback_snapshot(merged_payload))

        validation_error = cls._validate_setup_payload(merged_payload)
        if validation_error:
            cls._fail_setup(None, validation_error, cleanup=rollback)
        cls._set_progress("system", "running", "写入 .env 配置")
        env_path = cls.write_env(merged_payload)
        system_ok, system_message = cls._check_system(merged_payload, env_path)
        if not system_ok:
            cls._fail_setup("system", system_message, cleanup=rollback)
        cls._set_progress("system", "success", system_message)
        result: dict[str, dict[str, object] | str] = {"env_path": str(env_path)}
        result["system"] = cls._build_check(True, system_message)
        cls._set_progress("database", "running", "初始化数据库")
        try:
            superuser_created = await cls.bootstrap_database(merged_payload)
            database_message = "数据库初始化完成"
        except Exception as exc:
            detail = cls._error_detail(exc)
            cls._fail_setup("database", f"数据库初始化失败: {detail}", cleanup=rollback)
        cls._set_progress("database", "success", database_message)
        result["database"] = cls._build_check(True, database_message)
        try:
            await reload_runtime()
        except Exception as exc:
            detail = cls._error_detail(exc)
            cls._fail_setup("database", f"数据库配置重载失败: {detail}", cleanup=rollback)
        superuser_message = "超级管理员已创建" if superuser_created else "超级管理员已存在"
        cls._set_progress("superuser", "success", superuser_message)
        result["superuser"] = cls._build_check(True, superuser_message)
        cls._set_progress("redis", "running", "检查 Redis 连接")
        redis_ok, redis_message, redis_skipped = await cls._check_redis(merged_payload)
        if redis_skipped:
            cls._set_progress("redis", "skipped", redis_message, True)
            result["redis"] = cls._build_check(True, redis_message, True)
        else:
            if not redis_ok:
                cls._fail_setup("redis", redis_message, cleanup=rollback)
            cls._set_progress("redis", "success", redis_message)
            result["redis"] = cls._build_check(True, redis_message, False)
        await cls._finalize_setup_success(cleanup=rollback)
        return result

