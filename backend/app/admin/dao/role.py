"""
@File: role.py
@Author: GuaiMiu
@Date: 2025/4/7 11:35
@Version: 1.0
@Description:
"""

from app.crud.base import CurdBase
from app.admin.models.role import Role

role_curd: CurdBase[Role] = CurdBase(Role)
