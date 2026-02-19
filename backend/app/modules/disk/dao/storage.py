"""
@File: storage.py
@Author: GuaiMiu
@Date: 2026/2/7
@Version: 1.0
@Description:
"""

from app.crud.base import CurdBase
from app.modules.disk.models.storage import Storage

storage_crud: CurdBase[Storage] = CurdBase(Storage)

