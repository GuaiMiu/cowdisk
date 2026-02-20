"""
@File: refactor_demo.py
@Description: 新错误规范示例接口
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_session
from app.core.errors.codes import (
    CommonCode,
    FileCode,
    PermissionCode,
    ShareCode,
)
from app.core.response import ApiResponse, ok
from app.modules.admin.models.user import User
from app.modules.examples.services.domain_service import DomainDemoService
from app.shared.deps import require_user


class FileItemOut(BaseModel):
    id: int
    name: str
    parent_id: int | None
    is_dir: bool


class CreateFileIn(BaseModel):
    parent_id: int | None = Field(default=None)
    name: str = Field(min_length=1, max_length=255)
    is_dir: bool = False


class ShareItemOut(BaseModel):
    token: str
    name: str
    resource_type: str
    expires_at: str | None


class PermissionCheckOut(BaseModel):
    allowed: bool
    reason: str


common_error_responses = {
    400: {
        "description": "参数错误",
        "content": {
            "application/json": {
                "example": {"code": int(CommonCode.BAD_REQUEST), "message": "请求参数错误", "data": None}
            }
        },
    },
    401: {
        "description": "未认证",
        "content": {
            "application/json": {
                "example": {"code": 200001, "message": "未登录或登录已失效", "data": None}
            }
        },
    },
    500: {
        "description": "内部错误",
        "content": {
            "application/json": {
                "example": {"code": int(CommonCode.INTERNAL_ERROR), "message": "系统内部错误", "data": None}
            }
        },
    },
}


refactor_demo_router = APIRouter(prefix="", tags=["Refactor - Demo"], dependencies=[Depends(require_user)])


@refactor_demo_router.get(
    "/files/{file_id}",
    response_model=ApiResponse[FileItemOut],
    responses={
        **common_error_responses,
        404: {
            "description": "文件不存在",
            "content": {
                "application/json": {
                    "example": {"code": int(FileCode.FILE_NOT_FOUND), "message": "文件不存在", "data": None}
                }
            },
        },
    },
)
async def get_file_demo(
    file_id: int,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    row = await DomainDemoService.get_file_or_404(db=db, user_id=current_user.id, file_id=file_id)
    return ok(
        FileItemOut(
            id=row.id,
            name=row.name,
            parent_id=row.parent_id,
            is_dir=row.is_dir,
        ).model_dump()
    )


@refactor_demo_router.post(
    "/files",
    response_model=ApiResponse[FileItemOut],
    responses={
        **common_error_responses,
        409: {
            "description": "同名冲突",
            "content": {
                "application/json": {
                    "example": {"code": int(FileCode.NAME_CONFLICT), "message": "同级目录下已存在同名资源", "data": None}
                }
            },
        },
    },
)
async def create_file_demo(
    body: CreateFileIn,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    row = await DomainDemoService.create_file_with_conflict_check(
        db=db,
        user_id=current_user.id,
        parent_id=body.parent_id,
        name=body.name,
        is_dir=body.is_dir,
    )
    return ok(
        FileItemOut(
            id=row.id,
            name=row.name,
            parent_id=row.parent_id,
            is_dir=row.is_dir,
        ).model_dump(),
        message="创建成功",
    )


@refactor_demo_router.get(
    "/shares/{token}",
    response_model=ApiResponse[ShareItemOut],
    responses={
        **common_error_responses,
        404: {
            "description": "分享不存在",
            "content": {
                "application/json": {
                    "example": {"code": int(ShareCode.SHARE_NOT_FOUND), "message": "分享不存在", "data": None}
                }
            },
        },
        410: {
            "description": "分享已过期",
            "content": {
                "application/json": {
                    "example": {"code": int(ShareCode.SHARE_EXPIRED), "message": "分享已过期", "data": None}
                }
            },
        },
    },
)
async def get_share_demo(
    token: str,
    db: AsyncSession = Depends(get_async_session),
):
    row = await DomainDemoService.get_share_by_token(db=db, token=token)
    return ok(
        ShareItemOut(
            token=row.token,
            name=row.name,
            resource_type=row.resource_type,
            expires_at=row.expires_at.isoformat() if row.expires_at else None,
        ).model_dump()
    )


@refactor_demo_router.get(
    "/permissions/me/manage-files",
    response_model=ApiResponse[PermissionCheckOut],
    responses={
        **common_error_responses,
        403: {
            "description": "权限不足",
            "content": {
                "application/json": {
                    "example": {"code": int(PermissionCode.NO_PERMISSION), "message": "无权限访问该资源", "data": None}
                }
            },
        },
    },
)
async def check_manage_files_permission(
    current_user: User = Depends(require_user),
):
    await DomainDemoService.assert_can_manage_files(current_user)
    return ok(PermissionCheckOut(allowed=True, reason="超级管理员").model_dump())
