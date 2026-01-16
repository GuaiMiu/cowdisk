"""
@File: response.py
@Author: GuaiMiu
@Date: 2025/3/14 11:13
@Version: 1.0
@Description:
"""

from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.admin.models.response import ResponseModel


class Res:
    @staticmethod
    def success(
        data: Any = None,
        msg: str = "ok",
        code: int = 200,
        status_code: int = 200,
    ) -> JSONResponse:
        """返回成功的响应"""
        response = ResponseModel(code=code, msg=msg, data=data or {})
        return JSONResponse(status_code=status_code, content=jsonable_encoder(response))

    @staticmethod
    def error(
        msg: str = "error",
        code: int = 400,
        data: Any = None,
        status_code: int = 400,
    ) -> JSONResponse:
        """返回错误的响应"""
        response = ResponseModel(code=code, msg=msg, data=data or {})
        return JSONResponse(status_code=status_code, content=jsonable_encoder(response))
