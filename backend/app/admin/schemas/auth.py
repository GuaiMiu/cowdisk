"""
@File: auth.py
@Author: GuaiMiu
@Date: 2025/3/20 19:01
@Version: 1.0
@Description:
"""

import re

from pydantic import BaseModel, Field, EmailStr, model_validator

from app.core.exception import ServiceException


class TokenOut(BaseModel):
    """
    JWT Token输出模型
    """

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """
    JWT Payload模型
    """

    id: int | None = None
    username: str | None = None
    session_id: str | None = None


class UserRegisterIn(BaseModel):
    """
    用户注册输入模型
    """

    username: str = Field(max_length=20, min_length=4, description="用户名")
    password: str = Field(max_length=20, min_length=4, description="密码")
    mail: EmailStr = Field(description="邮箱")

    # @model_validator(mode="after")
    # def check_password(self) -> "UserRegisterIn":
    #     pattern = r"""^[^<>"'|\\]+$"""
    #     if self.password is None or re.match(pattern, self.password):
    #         return self
    #     else:
    #         raise ServiceException(msg="密码不能包含非法字符：< > \" ' \\ |")

    @model_validator(mode="before")
    @classmethod
    def check(cls, values):
        username = values.get("username", "").strip()
        password = values.get("password", "").strip()

        pattern = r"""^[^<>"'|\\]+$"""
        if not username and not password:
            raise ServiceException(msg="用户名或密码不能为空")
        if not re.match(pattern, password):
            raise ServiceException(msg="密码不能包含非法字符：< > \" ' \\ |")
        elif username == password:
            raise ServiceException(msg="用户名和密码不能相同")

        values["username"] = username
        values["password"] = password
        return values


class UserLoginIn(BaseModel):
    """
    用户登录输入模型
    """

    username: str = Field(max_length=20, min_length=4, description="用户名")
    password: str = Field(max_length=20, min_length=4, description="密码")
