"""
@File: middleware.py
@Author: GuaiMiu
@Date: 2025/3/14 11:12
@Version: 1.0
@Description:
"""

from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings


def handle_middleware(app: FastAPI):
    """
    全局中间件处理
    """
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS.split(",")
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=9)
