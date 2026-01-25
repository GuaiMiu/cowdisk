"""
@File: handle.py
@Author: GuaiMiu
@Date: 2025/3/14 11:12
@Version: 1.0
@Description:
"""

from fastapi import Request, Response, FastAPI
from fastapi.exceptions import RequestValidationError

from app.core.exception import (
    LoginException,
    ServiceException,
    AuthException,
    PermissionException,
)
from app.utils.logger import logger
from app.utils.response import Res


def handle_exception(app: FastAPI):
    """
    全局异常处理
    """

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> Response:
        """
        数据验证错误处理器
        :param request:
        :param exc:
        :return:
        """
        error_messages = []
        for error in exc.errors():
            error_messages.append(
                f"字段 {'.'.join(map(str, error['loc']))} 错误: {error['msg']}"
            )
        logger.error(f"请求 {request.url} 数据验证错误: {error_messages}")
        return Res.error(
            status_code=422, data=error_messages, msg="请求数据验证错误", code=422
        )

    @app.exception_handler(LoginException)
    async def login_exception_handler(
        request: Request,
        exc: LoginException,
    ) -> Response:
        """
        登录异常处理器
        :param request:
        :param exc:
        :return:
        """
        logger.warning(f"请求 {request.url} 登录异常: {exc.msg}")
        return Res.success(data=exc.data, msg=exc.msg or "登录失败")

    @app.exception_handler(AuthException)
    async def auth_exception_handler(
        request: Request,
        exc: AuthException,
    ) -> Response:
        """
        认证异常处理器
        :param request:
        :param exc:
        :return:
        """
        logger.warning(f"请求 {request.url} 认证异常: {exc.msg}")
        return Res.success(
            data=exc.data, msg=exc.msg or "认证失败", status_code=401, code=401
        )

    @app.exception_handler(PermissionException)
    async def permission_exception_handler(
        request: Request,
        exc: PermissionException,
    ) -> Response:
        """
        权限异常处理器
        :param request:
        :param exc:
        :return:
        """
        # logger.warning(f"请求 {request.url} 权限异常: {exc.msg}")
        return Res.success(
            data=exc.data, msg=exc.msg or "权限不足", status_code=403, code=403
        )

    @app.exception_handler(ServiceException)
    async def service_exception_handler(
        request: Request,
        exc: ServiceException,
    ) -> Response:
        """
        服务异常处理器
        :param request:
        :param exc:
        :return:
        """
        # logger.warning(f"请求 {request.url} 服务异常: {exc.msg}")
        return Res.error(msg=exc.msg or "服务异常", data=exc.data, code=400, status_code=400)

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request,
        exc: Exception,
    ):
        """
        服务器内部错误处理器
        :param request:
        :param exc:
        :return:
        """
        logger.error(f"请求 {request.url} 发生错误: {str(exc)}")
        return Res.error(
            status_code=500, data=None, msg=f"服务器内部错误: {str(exc)}", code=500
        )
