"""
@File: auth.py
@Author: GuaiMiu
@Date: 2025/3/18 11:35
@Version: 1.0
@Description:
"""

from app.crud.base import CurdBase
from app.modules.admin.models.user import User

user_crud: CurdBase[User] = CurdBase(User)

