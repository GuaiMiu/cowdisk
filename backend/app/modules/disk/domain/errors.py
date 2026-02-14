"""
@File: errors.py
@Author: GuaiMiu
@Date: 2026/2/7
@Version: 1.0
@Description: Disk 领域错误
"""

from app.core.exception import ServiceException


class DiskError(ServiceException):
    """
    统一的网盘领域异常
    """

    def __init__(self, msg: str, data: str | None = None):
        super().__init__(data=data, msg=msg)
