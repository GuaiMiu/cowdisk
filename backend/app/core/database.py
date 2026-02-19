"""
@File: database.py
@Author: GuaiMiu
@Date: 2025/3/14 14:51
@Version: 1.0
@Description:
"""

from functools import lru_cache

from redis import asyncio as aioredis
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.exception import ServiceException
from app.core.fake_redis import FakeRedis
from app.utils.logger import logger


class AsyncEngineProxy:
    def __init__(self):
        self._engine = None

    def set(self, engine):
        self._engine = engine

    def get(self):
        return self._engine

    def is_ready(self) -> bool:
        return self._engine is not None

    def __getattr__(self, name):
        if self._engine is None:
            raise ServiceException(msg="数据库未配置，请先完成安装配置")
        return getattr(self._engine, name)


class AsyncSessionProxy:
    def __init__(self):
        self._maker = None

    def set(self, maker):
        self._maker = maker

    def is_ready(self) -> bool:
        return self._maker is not None

    def __call__(self, *args, **kwargs):
        if self._maker is None:
            raise ServiceException(msg="数据库未配置，请先完成安装配置")
        return self._maker(*args, **kwargs)


def _build_async_database_url() -> str:
    if settings.DATABASE_URL:
        return settings.DATABASE_URL

    db_type = (settings.DATABASE_TYPE or "").lower().strip()
    if db_type == "sqlite":
        return "sqlite+aiosqlite:////app/config/data.db"

    required_fields = [
        settings.DATABASE_USER,
        settings.DATABASE_PASSWORD,
        settings.DATABASE_HOST,
        settings.DATABASE_PORT,
        settings.DATABASE_NAME,
    ]
    if any(field in (None, "") for field in required_fields):
        # logger.warning("数据库未配置完成，跳过数据库连接")
        return ""

    return (
        f"mysql+aiomysql://"
        f"{settings.DATABASE_USER}:"
        f"{settings.DATABASE_PASSWORD}@"
        f"{settings.DATABASE_HOST}:"
        f"{settings.DATABASE_PORT}/"
        f"{settings.DATABASE_NAME}"
    )


def is_database_configured() -> bool:
    if settings.DATABASE_URL:
        return True

    db_type = (settings.DATABASE_TYPE or "").lower().strip()
    if db_type == "sqlite":
        return True

    required_fields = [
        settings.DATABASE_USER,
        settings.DATABASE_PASSWORD,
        settings.DATABASE_HOST,
        settings.DATABASE_PORT,
        settings.DATABASE_NAME,
    ]
    return all(field not in (None, "") for field in required_fields)


def _create_async_engine(url: str):
    if url.startswith("sqlite+aiosqlite"):
        return create_async_engine(
            url,
            future=True,
            connect_args={"check_same_thread": False},
        )
    return create_async_engine(
        url,
        future=True,
        # echo=True,
        pool_size=10,  # 最大连接池大小
        max_overflow=20,  # 超出 pool_size 的连接数上限
        pool_recycle=1800,  # 回收连接时间，防止 MySQL “server has gone away”
    )


def _apply_database_config(url: str) -> None:
    global ASYNC_DATABASE_URL
    ASYNC_DATABASE_URL = url
    if not url:
        async_engine.set(None)
        async_session.set(None)
        return
    engine = _create_async_engine(url)
    async_engine.set(engine)
    async_session.set(
        async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    )


# 创建一个异步数据库引擎和会话
async_engine = AsyncEngineProxy()
async_session = AsyncSessionProxy()
ASYNC_DATABASE_URL = ""
_apply_database_config(_build_async_database_url())


# 获取异步数据库会话
async def get_async_session():
    if not async_session.is_ready():
        raise ServiceException(msg="数据库未配置，请先完成安装配置")
    async with async_session() as session:
        try:
            # logger.info("MySQL 连接成功")
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class RedisClient:
    """封装 Redis 连接池，提供全局 Redis 客户端"""

    def __init__(
        self,
        host: str,
        port: int,
        db: int,
        username: str = None,
        password: str = None,
        max_connections: int = 10,
    ):
        """初始化 Redis 连接池"""
        self.pool = aioredis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            username=username,
            password=password,
            decode_responses=True,
            max_connections=max_connections,
        )
        self.client = aioredis.Redis(connection_pool=self.pool)

    def get_client(self) -> aioredis.Redis:
        """获取 Redis 客户端"""
        return self.client

    async def close(self):
        """关闭 Redis 连接池"""
        if self.pool:
            await self.pool.disconnect()
            logger.info(f"{settings.APP_NAME} Redis 连接池已关闭")

    async def check_connection(self) -> bool:
        """检查 Redis 是否连接成功"""
        try:
            await self.client.ping()
            return True
        except (
            aioredis.AuthenticationError,
            aioredis.TimeoutError,
            aioredis.RedisError,
        ) as e:
            logger.error(f"Redis 连接失败: {e}")
            return False


redis_client = RedisClient(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    username=settings.REDIS_USERNAME,
    password=settings.REDIS_PASSWORD,
    max_connections=10,
)
fake_redis_client = FakeRedis()


async def reload_database():
    old_engine = async_engine.get()
    _apply_database_config(_build_async_database_url())
    new_engine = async_engine.get()
    if old_engine and old_engine is not new_engine:
        await old_engine.dispose()


async def reload_redis():
    global redis_client
    old_client = redis_client
    redis_client = RedisClient(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        username=settings.REDIS_USERNAME,
        password=settings.REDIS_PASSWORD,
        max_connections=10,
    )
    if old_client:
        await old_client.close()
    get_async_redis.cache_clear()


async def reload_runtime():
    from app.core.config import reload_settings

    reload_settings()
    await reload_database()
    await reload_redis()


@lru_cache
def get_async_redis():
    """根据配置返回 Redis 客户端或 FakeRedis"""
    if not settings.REDIS_ENABLE:
        logger.warning("Redis 已禁用，使用 FakeRedis 模拟客户端")
        return fake_redis_client
    else:
        return redis_client.get_client()
