"""
@File: auth.py
@Author: GuaiMiu
@Date: 2025/3/14 16:43
@Version: 1.0
@Description:
"""

from enum import Enum


class UserStatusEnum(int, Enum):
    ACTIVE = True  # 正常
    DELETED = False  # 停用
