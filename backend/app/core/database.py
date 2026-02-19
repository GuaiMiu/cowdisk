from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from redis import asyncio as aioredis
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.exception import ServiceException
from app.core.fake_redis import FakeRedis
from app.utils.logger import logger

DEFAULT_MYSQL_POOL_SIZE = 10
DEFAULT_MYSQL_MAX_OVERFLOW = 20
DEFAULT_MYSQL_POOL_RECYCLE = 1800


# ---------- Runtime Config ----------

@dataclass(frozen=True)
class DatabaseRuntimeConfig:
    url: str
    configured: bool
    drivername: str  # e.g. "mysql+aiomysql", "sqlite+aiosqlite"


@dataclass(frozen=True)
class RedisRuntimeConfig:
    enabled: bool
    host: str
    port: int
    db: int
    username: str | None
    password: str | None
    max_connections: int = 10


# ---------- Proxies ----------

class AsyncEngineProxy:
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None

    def set(self, engine: Optional[AsyncEngine]):
        self._engine = engine

    def get(self) -> Optional[AsyncEngine]:
        return self._engine

    def is_ready(self) -> bool:
        return self._engine is not None

    def __getattr__(self, name):
        if self._engine is None:
            raise ServiceException(msg="数据库未配置，请先完成安装配置")
        return getattr(self._engine, name)


class AsyncSessionProxy:
    def __init__(self):
        self._maker: Optional[async_sessionmaker[AsyncSession]] = None

    def set(self, maker: Optional[async_sessionmaker[AsyncSession]]):
        self._maker = maker

    def is_ready(self) -> bool:
        return self._maker is not None

    def __call__(self, *args, **kwargs):
        if self._maker is None:
            raise ServiceException(msg="数据库未配置，请先完成安装配置")
        return self._maker(*args, **kwargs)


# ---------- Database URL ----------


def _resolve_database_runtime_config() -> DatabaseRuntimeConfig:
    url = (settings.DATABASE_URL or "").strip()

    if not url:
        return DatabaseRuntimeConfig(
            url="",
            configured=False,
            drivername="",
        )

    u = make_url(url)
    return DatabaseRuntimeConfig(
        url=url,
        configured=True,
        drivername=u.drivername,
    )



def is_database_configured() -> bool:
    return _resolve_database_runtime_config().configured


def _create_db_engine(cfg: DatabaseRuntimeConfig) -> AsyncEngine:
    if cfg.drivername.startswith("sqlite"):
        return create_async_engine(
            cfg.url,
            future=True,
            connect_args={"check_same_thread": False},
            echo=getattr(settings, "SQL_ECHO", False),
        )

    # MySQL / others
    return create_async_engine(
        cfg.url,
        future=True,
        pool_size=DEFAULT_MYSQL_POOL_SIZE,
        max_overflow=DEFAULT_MYSQL_MAX_OVERFLOW,
        pool_recycle=DEFAULT_MYSQL_POOL_RECYCLE,
        pool_pre_ping=True,
        echo=getattr(settings, "SQL_ECHO", False),
    )


def _bind_database(cfg: DatabaseRuntimeConfig) -> None:
    global ASYNC_DATABASE_URL
    ASYNC_DATABASE_URL = cfg.url

    if not cfg.configured:
        async_engine.set(None)
        async_session.set(None)
        return

    engine = _create_db_engine(cfg)
    async_engine.set(engine)
    async_session.set(async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False))


# ---------- Redis ----------

class RedisClient:
    def __init__(self, config: RedisRuntimeConfig):
        self.config = config
        self.pool = aioredis.ConnectionPool(
            host=config.host,
            port=config.port,
            db=config.db,
            username=config.username,
            password=config.password,
            decode_responses=True,
            max_connections=config.max_connections,
        )
        self.client = aioredis.Redis(connection_pool=self.pool)

    def get_client(self) -> aioredis.Redis:
        return self.client

    async def close(self):
        await self.pool.disconnect()

    async def check_connection(self) -> bool:
        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis 连接失败: {e}")
            return False


def _resolve_redis_runtime_config() -> RedisRuntimeConfig:
    return RedisRuntimeConfig(
        enabled=bool(settings.REDIS_ENABLE),
        host=settings.REDIS_HOST,
        port=int(settings.REDIS_PORT),
        db=int(settings.REDIS_DB),
        username=settings.REDIS_USERNAME,
        password=settings.REDIS_PASSWORD,
        max_connections=10,
    )


def _create_redis_client(cfg: RedisRuntimeConfig) -> RedisClient:
    return RedisClient(cfg)


# ---------- Globals & lifecycle ----------

async_engine = AsyncEngineProxy()
async_session = AsyncSessionProxy()
ASYNC_DATABASE_URL = ""

_fake_redis = FakeRedis()
redis_client: RedisClient | None = None


def init_runtime() -> None:
    global redis_client
    db_cfg = _resolve_database_runtime_config()
    _bind_database(db_cfg)

    r_cfg = _resolve_redis_runtime_config()
    redis_client = _create_redis_client(r_cfg) if r_cfg.enabled else None


init_runtime()


async def get_async_session():
    if not async_session.is_ready():
        raise ServiceException(msg="数据库未配置，请先完成安装配置")

    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

_fake_redis_warned = False

def get_async_redis():
    global _fake_redis_warned
    if redis_client is None:
        if not _fake_redis_warned:
            logger.warning("Redis 已禁用，使用 FakeRedis 模拟客户端")
            _fake_redis_warned = True
        return _fake_redis
    return redis_client.get_client()


async def reload_database():
    old = async_engine.get()
    _bind_database(_resolve_database_runtime_config())
    new = async_engine.get()
    if old and old is not new:
        await old.dispose()


async def reload_redis():
    global redis_client
    old = redis_client
    r_cfg = _resolve_redis_runtime_config()
    redis_client = _create_redis_client(r_cfg) if r_cfg.enabled else None
    if old:
        await old.close()


async def reload_runtime():
    from app.core.config import reload_settings
    reload_settings()
    await reload_database()
    await reload_redis()
