"""
@File: init.py
@Author: GuaiMiu
@Date: 2025/3/14 15:51
@Version: 1.0
@Description:
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.core.database import async_session, async_engine, is_database_configured, redis_client
from app.modules.system.service.config import ConfigCenterService
from app.modules.system.services.setup import SetupService
from app.utils.logger import logger


@asynccontextmanager
async def app_init(_app: FastAPI):
    """
    初始化应用
    :param app:
    :return:
    """
    try:
        # logger.info(f"读取配置文件： {settings}")
        logger.info(f"{settings.APP_NAME} Starting...")
        if not is_database_configured():
            logger.warning("数据库未配置，跳过初始化")
        else:
            if not async_engine.is_ready() or not async_session.is_ready():
                raise RuntimeError("数据库连接未初始化")
            logger.info(f"{settings.APP_NAME} Database configuration ready.")
            async with async_session() as session:
                try:
                    await SetupService.ensure_rbac_seed(session)
                except OperationalError:
                    logger.warning("菜单/角色种子表尚未初始化，跳过 ensure_rbac_seed")
                except Exception as exc:
                    logger.warning("ensure_rbac_seed 执行失败: %s", exc)
                try:
                    await ConfigCenterService(session).ensure_defaults()
                except OperationalError:
                    logger.warning("配置表尚未初始化，跳过 ensure_defaults")
                except Exception as exc:
                    logger.warning("ensure_defaults 执行失败: %s", exc)
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
        engine = async_engine.get()
        if engine is not None:
            await engine.dispose()
        await redis_client.close()
        logger.info(f"{settings.APP_NAME} Closing...")
