"""
@File: menu.py
@Author: GuaiMiu
@Date: 2025/4/11 21:17
@Version: 1.0
@Description:
"""

from app.modules.admin.models.menu import Menu
from app.crud.base import CurdBase

menu_curd: CurdBase[Menu] = CurdBase(Menu)

