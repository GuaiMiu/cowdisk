"""
@File: main_router.py
@Author: GuaiMiu
@Date: 2025/3/15 09:47
@Version: 1.0
@Description:
"""

from fastapi import APIRouter
from starlette.responses import HTMLResponse

from app.admin.controller.auth import auth_router
from app.admin.controller.menu import menu_router
from app.admin.controller.role import role_router
from app.admin.controller.user import user_router
from app.core.config import settings
from app.disk.controller.disk import disk_download_router, disk_router
from app.disk.controller.share import share_manage_router, share_public_router

api_router = APIRouter(prefix=settings.APP_API_PREFIX)

api_router.include_router(auth_router)

admin_router = APIRouter(prefix="/admin")
admin_router.include_router(user_router)
admin_router.include_router(role_router)
admin_router.include_router(menu_router)


user_api_router = APIRouter(prefix="/user")
user_api_router.include_router(disk_router)
user_api_router.include_router(disk_download_router)

api_router.include_router(admin_router)
api_router.include_router(user_api_router)
api_router.include_router(share_manage_router)
api_router.include_router(share_public_router)
