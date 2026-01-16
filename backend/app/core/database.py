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
from app.core.fake_redis import FakeRedis
from app.utils.logger import logger

# 创建一个异步数据库引擎和会话
ASYNC_MYSQL_URL = (
    f"mysql+aiomysql://"
    f"{settings.DATABASE_USER}:"
    f"{settings.DATABASE_PASSWORD}@"
    f"{settings.DATABASE_HOST}:"
    f"{settings.DATABASE_PORT}/"
    f"{settings.DATABASE_NAME}"
)
db_type = (settings.DATABASE_TYPE or "").lower().strip()
if db_type == "sqlite":
    ASYNC_DATABASE_URL = settings.DATABASE_URL or "sqlite+aiosqlite:///./data.db"
else:
    ASYNC_DATABASE_URL = settings.DATABASE_URL or ASYNC_MYSQL_URL

if ASYNC_DATABASE_URL.startswith("sqlite+aiosqlite"):
    async_engine = create_async_engine(
        ASYNC_DATABASE_URL,
        future=True,
        connect_args={"check_same_thread": False},
    )
else:
    async_engine = create_async_engine(
        ASYNC_DATABASE_URL,
        future=True,
        # echo=True,
        pool_size=10,  # 最大连接池大小
        max_overflow=20,  # 超出 pool_size 的连接数上限
        pool_recycle=1800,  # 回收连接时间，防止 MySQL “server has gone away”
    )
async_session = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# 获取异步数据库会话
async def get_async_session():
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
        password: str = None,
        max_connections: int = 10,
    ):
        """初始化 Redis 连接池"""
        self.pool = aioredis.ConnectionPool(
            host=host,
            port=port,
            db=db,
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
    password=settings.REDIS_PASSWORD,
    max_connections=10,
)
fake_redis_client = FakeRedis()


@lru_cache
def get_async_redis():
    """根据配置返回 Redis 客户端或 FakeRedis"""
    if not settings.REDIS_ENABLE:
        logger.warning("Redis 已禁用，使用 FakeRedis 模拟客户端")
        return fake_redis_client
    else:
        return redis_client.get_client()
