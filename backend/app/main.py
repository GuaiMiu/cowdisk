"""
@File: main_router.py
@Author: GuaiMiu
@Date: 2025/3/14 11:11
@Version: 1.0
@Description:
"""

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.index import index_router
from app.api.v1.main_router import api_router
from app.core.config import settings
from app.core.init import app_init
from app.core.middleware import handle_middleware
from app.handle import handle_exception

openapi_tags = [
    {"name": "Admin - Auth", "description": "管理端认证与会话"},
    {"name": "Admin - Users", "description": "用户管理"},
    {"name": "Admin - Roles", "description": "角色管理"},
    {"name": "Admin - Menus", "description": "菜单与权限管理"},
    {"name": "Admin - Uploads", "description": "上传会话维护"},
    {"name": "Disk - Files", "description": "文件与目录"},
    {"name": "Disk - Upload", "description": "分片上传"},
    {"name": "Disk - Share", "description": "用户分享"},
    {"name": "Disk - Public Share", "description": "公开分享访问"},
    {"name": "Disk - Trash", "description": "回收站"},
    {"name": "Disk - Archive", "description": "压缩与解压任务"},
    {"name": "System - Config", "description": "系统配置中心"},
    {"name": "System - Audit", "description": "审计日志"},
    {"name": "System - Setup", "description": "安装引导"},
]

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=app_init,
    debug=settings.APP_DEBUG,
    openapi_tags=openapi_tags,
)
# 静态资源（品牌图等）
static_dir = Path.cwd() / "app" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount(f"{settings.APP_API_PREFIX}/static", StaticFiles(directory=static_dir), name="static")
# 注册路由
app.include_router(api_router)
app.include_router(index_router)
# 加载全局异常处理方法
handle_exception(app)
# 注册中间件
handle_middleware(app)

if __name__ == "__main__":
    uvicorn.run(
        app="app.main:app",
        host=settings.APP_HOST,
        reload=settings.APP_DEBUG,
        port=settings.APP_PORT,
        proxy_headers=True,
        forwarded_allow_ips="*",
        log_config="uvicorn_config.json",
        log_level="debug",
        workers=None if settings.APP_DEBUG else 1,
    )
