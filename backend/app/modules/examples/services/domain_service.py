"""
@File: domain_service.py
@Description: 重构规范示例服务（文件/分享/权限）
"""

from __future__ import annotations

from datetime import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.admin.models.user import User
from app.modules.disk.models.file import File
from app.modules.disk.models.share import Share
from app.core.errors.exceptions import (
    FileNotFound,
    NameConflict,
    NoPermission,
    ShareExpired,
    ShareNotFound,
)


class DomainDemoService:
    @staticmethod
    async def get_file_or_404(db: AsyncSession, user_id: int, file_id: int) -> File:
        stmt = select(File).where(
            File.id == file_id,
            File.user_id == user_id,
            File.is_deleted == False,
        )
        row = (await db.exec(stmt)).first()
        if not row:
            raise FileNotFound()
        return row

    @staticmethod
    async def create_file_with_conflict_check(
        db: AsyncSession,
        user_id: int,
        parent_id: int | None,
        name: str,
        is_dir: bool = False,
    ) -> File:
        exist_stmt = select(File.id).where(
            File.user_id == user_id,
            File.parent_id == parent_id,
            File.name == name,
            File.is_deleted == False,
        )
        if (await db.exec(exist_stmt)).first():
            raise NameConflict()
        row = File(
            user_id=user_id,
            parent_id=parent_id,
            name=name,
            is_dir=is_dir,
            size=0,
            mime_type=None,
            etag="",
            storage_id=1,
            storage_path=f"{user_id}/{name}",
            storage_path_hash=f"{user_id}:{name}",
            content_hash=None,
            is_deleted=False,
            deleted_at=None,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return row

    @staticmethod
    async def get_share_by_token(db: AsyncSession, token: str) -> Share:
        stmt = select(Share).where(
            Share.token == token,
            Share.is_deleted == False,
        )
        row = (await db.exec(stmt)).first()
        if not row:
            raise ShareNotFound()
        now = datetime.now()
        if row.status != 1:
            raise ShareExpired("分享已失效")
        if row.expires_at and row.expires_at < now:
            raise ShareExpired()
        return row

    @staticmethod
    async def assert_can_manage_files(current_user: User) -> None:
        if not current_user.is_superuser:
            raise NoPermission("仅超级管理员可执行此操作")

