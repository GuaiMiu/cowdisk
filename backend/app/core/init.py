"""
@File: init.py
@Author: GuaiMiu
@Date: 2025/3/14 15:51
@Version: 1.0
@Description:
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.admin.models.menu import Menu
from app.core.config import settings
from app.core.database import async_session, async_engine, redis_client
from app.utils.logger import logger
from app.admin.models.user import User


def _is_sqlite() -> bool:
    db_type = (settings.DATABASE_TYPE or "").lower().strip()
    if db_type:
        return db_type == "sqlite"
    db_url = settings.DATABASE_URL or ""
    return db_url.startswith("sqlite")


async def init_database(session: AsyncSession):
    """
    初始化数据库
    :return:
    """
    menus = await session.exec(select(Menu))
    if len(menus.all()) == 0:
        with open("app/sql/init.sql", "r", encoding="utf-8") as f:
            sql_script = f.read()  # 读取 SQL 文件的内容
            if _is_sqlite():
                sql_script = sql_script.replace("`backend`.", "")
                for statement in sql_script.split(";"):
                    statement = statement.strip()
                    if statement:
                        await session.execute(text(statement))
            else:
                await session.execute(text(sql_script))  # 执行 SQL 文件中的所有 SQL 语句
            await session.commit()  # 提交事务


async def init_user(session: AsyncSession):
    """
    初始化用户
    :param session:
    :return:
    """
    user = await session.exec(select(User))
    if len(user.all()) == 0:
        user = User(
            username=settings.SUPERUSER_NAME,
            password=User.create_password(settings.SUPERUSER_PASSWORD),
            nickname="笨牛管理员",
            mail=settings.SUPERUSER_MAIL,
            is_superuser=True,
        )
        session.add(user)
        await session.commit()
        logger.info(
            f"初始化超级管理员用户: 用户名: {settings.SUPERUSER_NAME} 密码: {settings.SUPERUSER_PASSWORD}"
        )


@asynccontextmanager
async def app_init(app: FastAPI):
    """
    初始化应用
    :param app:
    :return:
    """
    try:
        # logger.info(f"读取配置文件： {settings}")
        logger.info(f"{settings.APP_NAME} Starting...")
        # 初始化数据表
        async with async_engine.begin() as conn:
            logger.info(f"{settings.APP_NAME} Initialize database...")
            await conn.run_sync(SQLModel.metadata.create_all)
        # 初始化
        async with async_session() as session:
            await init_user(session)
            await init_database(session)
            logger.info(f"{settings.APP_NAME} Database initialized!")
        logger.info(f"{settings.APP_NAME} Database connection successful!")
        # 检查 Redis 连接
        if settings.REDIS_ENABLE:
            if not await redis_client.check_connection():
                exit(-1)
            logger.info(f"{settings.APP_NAME} Redis connection successful!")
        else:
            logger.info(f"{settings.APP_NAME} FakeRedis connection successful!")
        logger.info(f"{settings.APP_NAME} Start successful!")
        logger.info(
            """
        ┏┓　　　┏┓+ +
　　　┏┛┻━━━┛┻┓ + +
　　　┃　　　　　　　┃ 　
　　　┃　　　━　　　┃ ++ + + +
　　 ████━████ ┃+
　　　┃　　　　　　　┃ +
　　　┃　　　┻　　　┃
　　　┃　　　　　　　┃ + +
　　　┗━┓　　　┏━┛
　　　　　┃　　　┃　　　　　　　　　　　
　　　　　┃　　　┃ + + + +
　　　　　┃　　　┃　　　　Codes are far away from bugs with the animal protecting　　　
　　　　　┃　　　┃ + 　　　　神兽保佑,代码无bug　　
　　　　　┃　　　┃
　　　　　┃　　　┃　　+　　　　　　　　　
　　　　　┃　 　　┗━━━┓ + +
　　　　　┃ 　　　　　　　┣┓
　　　　　┃ 　　　　　　　┏┛
　　　　　┗┓┓┏━┳┓┏┛ + + + +
　　　　　　┃┫┫　┃┫┫
　　　　　　┗┻┛　┗┻┛+ + + +
"""
        )
        yield
    except Exception as e:
        # 捕获异常并记录错误
        logger.error(f"{settings.APP_NAME} An error occurred during startup: {e}")
        raise
    finally:
        await async_engine.dispose()
        await redis_client.close()
        logger.info(f"{settings.APP_NAME} Closing...")
