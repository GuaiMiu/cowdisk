"""
@File: main_router.py
@Author: GuaiMiu
@Date: 2025/3/14 11:11
@Version: 1.0
@Description:
"""

import uvicorn
from fastapi import FastAPI

from app.api.index import index_router
from app.api.v1.main_router import api_router
from app.core.config import settings
from app.core.init import app_init
from app.core.middleware import handle_middleware
from app.handle import handle_exception

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=app_init,
    debug=settings.APP_DEBUG,
)
# 注册路由
app.include_router(api_router)
app.include_router(index_router)
# 加载全局异常处理方法
handle_exception(app)
# 注册中间件
handle_middleware(app)

if __name__ == "__main__":
    uvicorn.run(
        app="app.main:app",
        host=settings.APP_HOST,
        reload=settings.APP_DEBUG,
        port=settings.APP_PORT,
        proxy_headers=True,
        forwarded_allow_ips="*",
        # log_config="uvicorn_config.json",
        log_level="debug",
        workers=None if settings.APP_DEBUG else 1,
    )
