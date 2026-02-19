"""
@File: main_router.py
@Author: GuaiMiu
@Date: 2025/3/15 09:47
@Version: 1.0
@Description:
"""

from fastapi import APIRouter
from starlette.responses import HTMLResponse

from app.modules.admin.controller.auth import auth_router
from app.modules.admin.controller.menu import menu_router
from app.modules.admin.controller.profile import profile_router
from app.modules.admin.controller.role import role_router
from app.modules.admin.controller.user import user_router
from app.modules.admin.controller.uploads import admin_upload_router
from app.core.config import settings
from app.modules.disk.controller.access import access_router
from app.modules.disk.controller.archives import archives_router
from app.modules.disk.controller.files import files_router
from app.modules.disk.controller.public_shares import public_shares_router
from app.modules.disk.controller.shares import shares_router
from app.modules.disk.controller.trash import trash_router
from app.modules.disk.controller.uploads import uploads_router
from app.modules.disk.controller.wopi import wopi_router
from app.modules.system.controller.config import system_config_router
from app.audit.router import audit_router
from app.modules.system.controller.setup import setup_router
from app.modules.system.controller.monitor import monitor_router

api_router = APIRouter(prefix=settings.APP_API_PREFIX)

api_router.include_router(auth_router)
api_router.include_router(profile_router)
api_router.include_router(system_config_router)

admin_router = APIRouter(prefix="/admin")
admin_router.include_router(user_router)
admin_router.include_router(role_router)
admin_router.include_router(menu_router)
admin_router.include_router(admin_upload_router)

system_router = APIRouter(prefix="/system")
system_router.include_router(audit_router)
system_router.include_router(setup_router)
system_router.include_router(monitor_router)

me_router = APIRouter(prefix="/me")
me_router.include_router(files_router)
me_router.include_router(uploads_router)
me_router.include_router(trash_router)
me_router.include_router(archives_router)
me_router.include_router(shares_router)

public_router = APIRouter(prefix="/public")
public_router.include_router(public_shares_router)

api_router.include_router(admin_router)
api_router.include_router(system_router)
api_router.include_router(me_router)
api_router.include_router(public_router)
api_router.include_router(access_router)
api_router.include_router(wopi_router)

