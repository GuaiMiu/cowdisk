"""
@File: response.py
@Description: 统一 API 响应结构
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.errors.codes import CommonCode

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = Field(description="业务码")
    message: str = Field(description="人类可读消息")
    data: T | None = Field(description="响应数据，失败时固定为 null")


def ok(data: Any, message: str = "OK", http_status: int = 200) -> JSONResponse:
    payload = ApiResponse[Any](
        code=int(CommonCode.OK),
        message=message,
        data=data,
    )
    return JSONResponse(status_code=http_status, content=jsonable_encoder(payload))


def error(
    code: int,
    message: str,
    http_status: int,
) -> JSONResponse:
    payload = ApiResponse[None](
        code=code,
        message=message,
        data=None,
    )
    return JSONResponse(status_code=http_status, content=jsonable_encoder(payload))

