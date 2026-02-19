"""
@File: setup.py
@Author: GuaiMiu
@Date: 2026/02/09
@Version: 1.0
@Description: 初次安装引导接口
"""

from typing import Literal

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.modules.admin.models.response import ResponseModel
from app.core.config import settings
from app.core.database import get_async_session
from app.modules.admin.models.user import User
from app.modules.system.deps import get_config
from app.modules.system.services.branding import BrandingService
from app.modules.system.typed.config import Config
from app.modules.system.typed.keys import ConfigKey
from app.modules.system.typed.specs import get_default
from app.modules.system.services.install_state import InstallStateService
from app.modules.system.services.setup import SetupService
from app.shared.deps import require_permissions, require_user
from sqlmodel.ext.asyncio.session import AsyncSession

setup_router = APIRouter(prefix="/setup", tags=["System - Setup"])


class SetupStatusOut(BaseModel):
    """
    安装状态输出模型。
    """

    installed: bool = Field(..., description="是否已安装")
    phase: str = Field(..., description="安装阶段")
    message: str | None = Field(default=None, description="阶段消息")
    updated_at: str | None = Field(default=None, description="状态更新时间")


class SetupPayload(BaseModel):
    """
    安装引导输入模型。
    """

    database_url: str = Field(..., description="数据库连接 URL")
    app_name: str | None = Field(default=None, description="应用名称")
    superuser_name: str = Field(..., description="超级管理员账号")
    superuser_password: str = Field(..., description="超级管理员密码")
    superuser_mail: str = Field(..., description="超级管理员邮箱")
    allow_register: bool = Field(default=True, description="是否允许注册")
    redis_enable: bool = Field(default=False, description="是否启用 Redis")
    redis_auth_mode: Literal["none", "password", "username_password"] | None = Field(
        default=None, description="Redis 认证方式"
    )
    redis_host: str | None = Field(default=None, description="Redis 主机")
    redis_port: int | None = Field(default=None, description="Redis 端口")
    redis_username: str | None = Field(default=None, description="Redis 用户名")
    redis_password: str | None = Field(default=None, description="Redis 密码")
    redis_db: int | None = Field(default=None, description="Redis DB")
    storage_path: str = Field(..., description="文件存储路径")


class SetupCheckOut(BaseModel):
    ok: bool = Field(..., description="检查是否通过")
    message: str = Field(..., description="检查信息")
    skipped: bool = Field(default=False, description="是否跳过检查")


class SetupResultOut(BaseModel):
    env_path: str = Field(..., description=".env 写入路径")
    system: SetupCheckOut
    database: SetupCheckOut
    superuser: SetupCheckOut
    redis: SetupCheckOut


class SetupProgressStep(BaseModel):
    status: str = Field(..., description="进度状态")
    message: str = Field(..., description="进度消息")
    skipped: bool = Field(default=False, description="是否跳过")


class SetupProgressOut(BaseModel):
    steps: dict[str, SetupProgressStep] = Field(..., description="步骤进度")


class SetupFormDefaultsOut(BaseModel):
    app_name: str
    database_url: str
    superuser_name: str
    superuser_mail: str
    allow_register: bool
    redis_enable: bool
    redis_host: str
    redis_port: int
    redis_auth_mode: str
    redis_username: str
    redis_db: int
    storage_path: str


class PublicConfigOut(BaseModel):
    site_name: str = Field(..., description="站点名称")
    site_logo_url: str = Field(default="", description="站点 Logo URL")
    site_favicon_url: str = Field(default="", description="站点 Favicon URL")
    login_background_url: str = Field(default="", description="登录背景图 URL")
    theme_image_url: str = Field(default="", description="主题图 URL")


class SiteLogoUploadOut(BaseModel):
    asset_id: str = Field(..., description="资产ID")
    asset_url: str = Field(..., description="资源访问URL")


@setup_router.get(
    "/status",
    summary="获取安装状态",
    response_model=ResponseModel[SetupStatusOut],
)
async def get_setup_status(
):
    """
    获取系统是否已完成安装。
    """
    state = InstallStateService.get_status()
    return ResponseModel.success(
        data=SetupStatusOut(
            installed=state.installed,
            phase=state.phase,
            message=state.message,
            updated_at=state.updated_at,
        )
    )


@setup_router.post(
    "",
    summary="提交安装配置",
    response_model=ResponseModel[SetupResultOut],
)
async def submit_setup(payload: SetupPayload):
    """
    提交首次安装配置。
    写入 .env 并初始化数据库配置表。
    """
    if InstallStateService.get_status().phase == "DONE":
        return ResponseModel.error(msg="系统已完成安装，禁止重复初始化")
    result = await SetupService.run_setup(payload.model_dump())
    return ResponseModel.success(data=result, msg="配置已保存并自动生效")


@setup_router.get(
    "/progress",
    summary="获取安装进度",
    response_model=ResponseModel[SetupProgressOut],
)
async def get_setup_progress():
    """
    获取当前安装进度。
    """
    steps = SetupService.get_progress()
    return ResponseModel.success(data=SetupProgressOut(steps=steps))


@setup_router.get(
    "/defaults",
    summary="获取安装默认值",
    response_model=ResponseModel[SetupFormDefaultsOut],
)
async def get_setup_defaults():
    return ResponseModel.success(
        data=SetupFormDefaultsOut.model_validate(SetupService.get_form_defaults())
    )


@setup_router.get(
    "/public-config",
    summary="获取公开系统配置",
    response_model=ResponseModel[PublicConfigOut],
)
async def get_public_config(
    config: Config = Depends(get_config),
):
    site_name = (settings.APP_NAME or "").strip() or str(
        get_default(ConfigKey.SYSTEM_SITE_NAME, "CowDisk")
    )
    site_logo_url = ""
    site_favicon_url = ""
    login_background_url = ""
    theme_image_url = ""
    # 安装前或表结构未就绪时，不依赖动态配置表。
    if InstallStateService.get_status().phase == "DONE":
        try:
            dynamic_site_name = await config.system.site_name()
            if (dynamic_site_name or "").strip():
                site_name = dynamic_site_name.strip()
            site_logo_url = (await config.system.site_logo_url() or "").strip()
            site_favicon_url = (await config.system.site_favicon_url() or "").strip()
            login_background_url = (await config.system.login_background_url() or "").strip()
            theme_image_url = (await config.system.theme_image_url() or "").strip()
        except (OperationalError, ProgrammingError):
            pass
    return ResponseModel.success(
        data=PublicConfigOut(
            site_name=site_name,
            site_logo_url=site_logo_url,
            site_favicon_url=site_favicon_url,
            login_background_url=login_background_url,
            theme_image_url=theme_image_url,
        )
    )


@setup_router.post(
    "/site-asset/{asset_type}",
    summary="上传站点资源",
    response_model=ResponseModel[SiteLogoUploadOut],
    dependencies=[require_permissions(["cfg:core:write"])],
)
async def upload_site_asset(
    asset_type: str,
    logo: UploadFile = File(...),
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    data = await BrandingService.upload_site_asset(
        db=db,
        upload=logo,
        asset_type=asset_type,
        updated_by=current_user.id,
    )
    return ResponseModel.success(data=SiteLogoUploadOut.model_validate(data))




