"""
@File: response.py
@Author: GuaiMiu
@Date: 2025/3/14 11:13
@Version: 1.0
@Description:
"""

from datetime import datetime
from typing import Union

from pydantic import BaseModel, Field


class ResponseModel[T](BaseModel):
    code: int = Field(default=200, description="Response code")
    msg: str = Field(default="Success", description="Response message")
    data: Union[T, list[T], None] = Field(default=None, description="Response data")
    time: datetime = Field(
        default_factory=datetime.now,
        description="Response time",
    )

    @classmethod
    def success(
        cls, data: Union[T, list[T], None] = None, msg: str = "Success", code: int = 200
    ):
        return cls(code=code, msg=msg, data=data)

    @classmethod
    def error(cls, msg: str, code: int = 400, data: Union[T, list[T], None] = None):
        return cls(code=code, msg=msg, data=data)

    @classmethod
    def warning(cls, msg: str, code: int = 300, data: Union[T, list[T], None] = None):
        return cls(code=code, msg=msg, data=data)
