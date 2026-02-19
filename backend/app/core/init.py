from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import OperationalError

import app.core.database as db_runtime
from app.core.config import settings
from app.modules.system.services.config import ConfigCenterService
from app.modules.system.services.setup import SetupService
from app.utils.logger import logger


async def _safe_db_init(session):
    # RBAC seed
    try:
        await SetupService.ensure_rbac_seed(session)
    except OperationalError:
        logger.warning("RBAC/菜单/角色相关表尚未初始化，跳过 ensure_rbac_seed")
    except Exception as exc:
        logger.warning("ensure_rbac_seed 执行失败: %s", exc)

    # Config defaults
    try:
        await ConfigCenterService(session).ensure_defaults()
    except OperationalError:
        logger.warning("配置表尚未初始化，跳过 ensure_defaults")
    except Exception as exc:
        logger.warning("ensure_defaults 执行失败: %s", exc)


@asynccontextmanager
async def app_init(_app: FastAPI):
    logger.info("%s Starting...", settings.APP_NAME)

    try:
        # ---- Database init (optional during install) ----
        if not db_runtime.is_database_configured():
            logger.warning("数据库未配置（可能处于安装向导阶段），跳过数据库初始化")
        else:
            if not db_runtime.async_engine.is_ready() or not db_runtime.async_session.is_ready():
                raise RuntimeError("数据库已配置但 Engine/Session 未初始化（bind 失败）")

            logger.info("%s Database ready.", settings.APP_NAME)
            async with db_runtime.async_session() as session:
                await _safe_db_init(session)

        # ---- Redis check ----
        if db_runtime.redis_client is None:
            logger.info("%s Redis disabled -> FakeRedis ready.", settings.APP_NAME)
        else:
            ok = await db_runtime.redis_client.check_connection()
            if not ok:
                raise RuntimeError("Redis connection failed")
            logger.info("%s Redis connection successful.", settings.APP_NAME)

        logger.info("%s Start successful!", settings.APP_NAME)
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
        logger.error("%s Startup failed: %s", settings.APP_NAME, e)
        raise

    finally:
        # ---- Shutdown ----
        try:
            engine = db_runtime.async_engine.get()
            if engine is not None:
                await engine.dispose()
        except Exception as e:
            logger.warning("Dispose engine failed: %s", e)

        try:
            if db_runtime.redis_client is not None:
                await db_runtime.redis_client.close()
        except Exception as e:
            logger.warning("Close redis failed: %s", e)

        logger.info("%s Closing...", settings.APP_NAME)

