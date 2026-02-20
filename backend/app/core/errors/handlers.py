"""
@File: handlers.py
@Description: 全局异常处理（HTTP Status + 业务码）
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.errors.codes import CommonCode
from app.core.errors.exceptions import AppException
from app.core.response import error
from app.utils.logger import logger


def _format_validation_error(exc: RequestValidationError) -> str:
    parts: list[str] = []
    for item in exc.errors():
        loc = ".".join(str(x) for x in item.get("loc", []))
        msg = item.get("msg", "参数错误")
        if loc:
            parts.append(f"{loc}: {msg}")
        else:
            parts.append(str(msg))
    return "; ".join(parts) if parts else "请求参数错误"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def handle_app_exception(_: Request, exc: AppException):
        return error(code=exc.code, message=exc.message, http_status=exc.http_status)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_exception(_: Request, exc: RequestValidationError):
        return error(
            code=int(CommonCode.BAD_REQUEST),
            message=_format_validation_error(exc),
            http_status=400,
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(_: Request, exc: IntegrityError):
        logger.warning("DB integrity error: %s", str(exc))
        return error(
            code=int(CommonCode.CONFLICT),
            message="资源冲突",
            http_status=409,
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_sqlalchemy_error(_: Request, exc: SQLAlchemyError):
        logger.error("DB error: %s", str(exc))
        return error(
            code=int(CommonCode.INTERNAL_ERROR),
            message="系统内部错误",
            http_status=500,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception):
        logger.exception("Unhandled error: %s %s", str(request.url), str(exc))
        return error(
            code=int(CommonCode.INTERNAL_ERROR),
            message="系统内部错误",
            http_status=500,
        )
