"""
@File: exception.py
@Author: GuaiMiu
@Date: 2025/3/19 14:46
@Version: 1.0
@Description:
"""


class LoginException(Exception):
    """
    自定义登录异常LoginException
    """

    def __init__(self, data: str | None = None, msg: str | None = None):
        self.data = data
        self.msg = msg


class AuthException(Exception):
    """
    自定义认证异常AuthException
    """

    def __init__(self, data: str | None = None, msg: str | None = None):
        self.data = data
        self.msg = msg


class PermissionException(Exception):
    """
    自定义权限异常PermissionException
    """

    def __init__(self, data: str | None = None, msg: str | None = None):
        self.data = data
        self.msg = msg


class ServiceException(Exception):
    """
    自定义服务异常ServiceException
    """

    def __init__(self, data: str | None = None, msg: str | None = None):
        self.data = data
        self.msg = msg
