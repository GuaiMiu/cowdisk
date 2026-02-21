"""
@File: file.py
@Author: GuaiMiu
@Date: 2026/2/7
@Version: 1.0
@Description: 文件服务(以 DB 为真相)
"""

from __future__ import annotations

import asyncio
import json
import io
import mimetypes
import secrets
import time
import tempfile
from contextvars import ContextVar, Token
from datetime import datetime
from uuid import uuid4
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path, PurePosixPath

from fastapi import Request, UploadFile
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse, Response
from sqlalchemy.exc import IntegrityError
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession
import zipstream
from PIL import Image, ImageOps, UnidentifiedImageError

from app.modules.admin.dao.user import user_crud
from app.core.config import settings
from app.core.database import async_session, get_async_redis
from app.core.errors.exceptions import (
    BadRequestException,
    ChunkIncomplete,
    FileNotFound,
    FileTokenExpired,
    FileTokenInvalid,
    InvalidFileName,
    InvalidPage,
    InvalidPageSize,
    InvalidPartNumber,
    InvalidTargetType,
    InvalidTotalParts,
    InvalidUploadId,
    MoveToDescendant,
    MoveToSelf,
    NameConflict,
    NoPermission,
    ParentNotDirectory,
    PayloadTooLarge,
    PreviewNotSupported,
    QuotaExceeded,
    RestoreParentDeleted,
    RestoreParentMissing,
    StorageConfigNotFound,
    StorageMismatch,
    TaskInvalid,
    TaskNotReady,
    ThumbnailBuildFailed,
    ThumbnailNotSupported,
    UploadFinalizing,
    UploadSessionCompleted,
    UploadSessionNotFound,
    UserNotFound,
    ZipTargetRequired,
    ZipTooManyConflicts,
)
from app.utils.logger import logger
from app.modules.disk.domain.paths import (
    build_storage_path,
    build_trash_path,
    ensure_name,
    rel_path_from_storage,
)
from app.modules.disk.models.file import File
from app.modules.disk.models.storage import Storage
from app.modules.disk.storage.backends import get_storage_backend
from app.modules.disk.storage.streaming import (
    build_file_response as _build_file_response,
    build_inline_response as _build_inline_response,
    cleanup_abs_path as _cleanup_abs_path,
    content_disposition,
)
from app.modules.system.services.config import build_runtime_config
from app.modules.system.typed.config import Config
from app.audit.decorator import audited
from app.modules.admin.models.user import User


def _audit_resource_type_from_entry(entry: File | None) -> str:
    if entry and entry.is_dir:
        return "FOLDER"
    return "FILE"


def _audit_file_detail(entry: File | None) -> dict:
    if not entry:
        return {}
    return {
        "resource_id": str(entry.id),
        "path": rel_path_from_storage(entry.user_id, entry.storage_path),
        "resource_type": _audit_resource_type_from_entry(entry),
        "detail": {
            "name": entry.name,
            "size": entry.size,
            "is_dir": entry.is_dir,
        },
    }


async def _extract_from_result(*_args, **_kwargs):
    result = _kwargs.get("result")
    if isinstance(result, File):
        return _audit_file_detail(result)
    entry = getattr(result, "entry", None)
    if isinstance(entry, File):
        return _audit_file_detail(entry)
    return {}


async def _extract_download(*_args, **_kwargs):
    db = _kwargs.get("db")
    file_id = _kwargs.get("file_id")
    if not db or not file_id:
        return {}
    entry = await db.get(File, file_id)
    if not entry:
        return {"resource_id": str(file_id), "path": str(file_id)}
    return _audit_file_detail(entry)


class FileService:
    _UPLOAD_BUFFER_SIZE = int(settings.DISK_UPLOAD_BUFFER_SIZE or 1024 * 1024)
    _UPLOAD_CONCURRENCY_LIMIT = int(settings.DISK_UPLOAD_CONCURRENCY or 3)
    _upload_semaphores: dict[int, tuple[int, asyncio.Semaphore]] = {}
    _upload_semaphore_lock = asyncio.Lock()
    _runtime_config_ctx: ContextVar[Config | None] = ContextVar(
        "file_service_runtime_config",
        default=None,
    )

    class _UploadCancelled(Exception):
        pass

    @dataclass(frozen=True)
    class DownloadResult:
        response: Response
        entry: File

    @classmethod
    def bind_config(cls, config: Config) -> Token[Config | None]:
        return cls._runtime_config_ctx.set(config)

    @classmethod
    def unbind_config(cls, token: Token[Config | None]) -> None:
        cls._runtime_config_ctx.reset(token)

    @classmethod
    def _cfg(cls, db: AsyncSession) -> Config:
        runtime_cfg = cls._runtime_config_ctx.get()
        if runtime_cfg is not None:
            return runtime_cfg
        return build_runtime_config(db, request_cache={})

    @classmethod
    async def _get_upload_semaphore(cls, user_id: int, db: AsyncSession) -> asyncio.Semaphore:
        cfg = cls._cfg(db)
        limit = await cfg.upload.max_concurrency_per_user()
        limit = max(int(limit or 1), 1)
        async with cls._upload_semaphore_lock:
            # TODO: 多实例场景需改用分布式限流/锁。
            existing = cls._upload_semaphores.get(user_id)
            if existing and existing[0] == limit:
                return existing[1]
            semaphore = asyncio.Semaphore(limit)
            cls._upload_semaphores[user_id] = (limit, semaphore)
            return semaphore

    @classmethod
    async def _with_upload_limit(cls, user_id: int, db: AsyncSession, coro):
        semaphore = await cls._get_upload_semaphore(user_id, db)
        await semaphore.acquire()
        try:
            return await coro
        finally:
            semaphore.release()

    @classmethod
    async def get_default_storage(cls, db: AsyncSession) -> Storage:
        """
        获取默认存储配置。
        若不存在则自动创建本地存储配置。
        默认存储类型为 local，路径来源于配置。
        仅用于初始化与兜底，不应频繁调用。
        权限假设：调用方已完成用户鉴权。
        并发：存在轻微竞争，但最终一致。
        性能：单次查询 + 可能的插入。
        返回：Storage 实例。
        """
        stmt = select(Storage).where(Storage.type == "local")
        storage = (await db.exec(stmt)).first()
        if storage:
            return storage
        cfg = cls._cfg(db)
        storage_path = await cfg.storage.path()
        storage = Storage(
            type="local",
            base_path_or_bucket=str(storage_path),
            config_text="",
        )
        db.add(storage)
        await db.commit()
        await db.refresh(storage)
        return storage

    @classmethod
    async def _get_storage_by_id(cls, db: AsyncSession, storage_id: int) -> Storage:
        stmt = select(Storage).where(Storage.id == storage_id)
        storage = (await db.exec(stmt)).first()
        if not storage:
            raise StorageConfigNotFound()
        return storage

    @staticmethod
    def _hash_storage_path(storage_path: str) -> str:
        return sha1(storage_path.encode("utf-8")).hexdigest()

    @staticmethod
    def _session_ttl() -> int:
        return int(settings.UPLOAD_SESSION_TTL or 24 * 3600)

    @staticmethod
    def _done_ttl() -> int:
        return int(settings.UPLOAD_DONE_TTL or 3600)

    @staticmethod
    def _upload_reservation_key(user_id: int, upload_id: str) -> str:
        return f"disk:quota:reservation:{user_id}:{upload_id}"

    @staticmethod
    def _upload_reservation_index_key(user_id: int) -> str:
        return f"disk:quota:reservation_index:{user_id}"

    @staticmethod
    def _parse_positive_int(value: object) -> int:
        try:
            parsed = int(value or 0)
        except (TypeError, ValueError):
            return 0
        return parsed if parsed > 0 else 0

    @classmethod
    async def _sum_upload_reservations(
        cls,
        redis,
        user_id: int,
        exclude_upload_id: str | None = None,
    ) -> int:
        index_key = cls._upload_reservation_index_key(user_id)
        upload_ids = await redis.smembers(index_key)
        if not upload_ids:
            return 0
        total = 0
        stale_ids: list[str] = []
        for raw_upload_id in upload_ids:
            current_upload_id = str(raw_upload_id)
            if exclude_upload_id and current_upload_id == exclude_upload_id:
                continue
            item_key = cls._upload_reservation_key(user_id, current_upload_id)
            reserved_raw = await redis.get(item_key)
            if reserved_raw is None:
                stale_ids.append(current_upload_id)
                continue
            total += cls._parse_positive_int(reserved_raw)
        if stale_ids:
            await redis.srem(index_key, *stale_ids)
        return total

    @classmethod
    async def _reserve_upload_quota(
        cls,
        db: AsyncSession,
        redis,
        user_id: int,
        upload_id: str,
        reserved_bytes: int,
    ) -> None:
        if reserved_bytes <= 0:
            return
        user = await cls._get_user_for_update(db, user_id)
        total_space = int(user.total_space or 0)
        if total_space > 0:
            used_space = await cls._current_used_space(db, user_id)
            reserved_total = await cls._sum_upload_reservations(redis, user_id)
            remaining = total_space - used_space - reserved_total
            if reserved_bytes > remaining:
                raise QuotaExceeded()
        item_key = cls._upload_reservation_key(user_id, upload_id)
        index_key = cls._upload_reservation_index_key(user_id)
        ttl = cls._session_ttl()
        await redis.set(item_key, str(reserved_bytes), ex=ttl)
        await redis.sadd(index_key, upload_id)
        await redis.expire(index_key, ttl * 2)

    @classmethod
    async def _get_upload_reserved_bytes(cls, redis, user_id: int, upload_id: str) -> int:
        item_key = cls._upload_reservation_key(user_id, upload_id)
        value = await redis.get(item_key)
        return cls._parse_positive_int(value)

    @classmethod
    async def _release_upload_reservation(cls, redis, user_id: int, upload_id: str) -> None:
        item_key = cls._upload_reservation_key(user_id, upload_id)
        index_key = cls._upload_reservation_index_key(user_id)
        await redis.delete(item_key)
        await redis.srem(index_key, upload_id)

    @classmethod
    async def _touch_upload_reservation(cls, redis, user_id: int, upload_id: str) -> None:
        item_key = cls._upload_reservation_key(user_id, upload_id)
        ttl = await redis.ttl(item_key)
        if ttl == -2:
            return
        session_ttl = cls._session_ttl()
        await redis.expire(item_key, session_ttl)
        await redis.expire(cls._upload_reservation_index_key(user_id), session_ttl * 2)

    @classmethod
    async def _download_token_ttl(cls, db: AsyncSession) -> int:
        cfg = cls._cfg(db)
        ttl = await cfg.download.token_ttl_seconds()
        if isinstance(ttl, str):
            ttl = ttl.strip().strip('"').strip("'")
        return int(ttl or 7200)

    @classmethod
    async def _preview_token_ttl(cls, db: AsyncSession) -> int:
        cfg = cls._cfg(db)
        ttl = await cfg.preview.max_duration_seconds()
        return int(ttl)

    @classmethod
    async def _get_user_for_update(cls, db: AsyncSession, user_id: int) -> User:
        stmt = select(User).where(User.id == user_id).with_for_update()
        user = (await db.exec(stmt)).first()
        if not user:
            raise UserNotFound()
        return user

    @classmethod
    async def _current_used_space(cls, db: AsyncSession, user_id: int) -> int:
        stmt = select(func.coalesce(func.sum(File.size), 0)).where(
            File.user_id == user_id,
            File.is_deleted == False,
            File.is_dir == False,
        )
        return int((await db.exec(stmt)).one() or 0)

    @classmethod
    async def _ensure_quota_available(
        cls,
        db: AsyncSession,
        user_id: int,
        required_bytes: int,
        exclude_upload_id: str | None = None,
    ) -> None:
        if required_bytes <= 0:
            return
        user = await cls._get_user_for_update(db, user_id)
        total_space = int(user.total_space or 0)
        if total_space <= 0:
            return
        used_space = await cls._current_used_space(db, user_id)
        redis = get_async_redis()
        reserved_total = await cls._sum_upload_reservations(
            redis,
            user_id,
            exclude_upload_id=exclude_upload_id,
        )
        remaining = total_space - used_space - reserved_total
        if required_bytes > remaining:
            raise QuotaExceeded()

    @classmethod
    async def _upload_max_size_bytes(cls, db: AsyncSession) -> int | None:
        cfg = cls._cfg(db)
        max_mb = await cfg.upload.max_single_file_mb()
        if max_mb is None or max_mb == "":
            return None
        try:
            return int(max_mb) * 1024 * 1024
        except (TypeError, ValueError):
            return None

    @classmethod
    async def _upload_chunk_size_bytes(cls, db: AsyncSession) -> int:
        cfg = cls._cfg(db)
        chunk_mb = await cfg.upload.chunk_size_mb()
        try:
            return max(int(chunk_mb), 1) * 1024 * 1024
        except (TypeError, ValueError):
            return 8 * 1024 * 1024

    @staticmethod
    def _make_upload_id(total_parts: int) -> str:
        return f"{total_parts}-{uuid4().hex}"

    @staticmethod
    def _parse_upload_id(upload_id: str) -> int | None:
        if not upload_id:
            return None
        prefix = upload_id.split("-", 1)[0]
        if prefix.isdigit():
            return int(prefix)
        return None

    @classmethod
    async def _get_active_file(
        cls, db: AsyncSession, user_id: int, file_id: int
    ) -> File:
        stmt = select(File).where(
            File.id == file_id,
            File.user_id == user_id,
            File.is_deleted == False,
        )
        file = (await db.exec(stmt)).first()
        if not file:
            raise FileNotFound("文件或目录不存在")
        return file

    @classmethod
    async def _get_active_dir(
        cls, db: AsyncSession, user_id: int, parent_id: int
    ) -> File:
        parent = await cls._get_active_file(db, user_id, parent_id)
        if not parent.is_dir:
            raise ParentNotDirectory()
        return parent

    @classmethod
    async def _ensure_unique_name(
        cls,
        db: AsyncSession,
        user_id: int,
        parent_id: int | None,
        name: str,
        exclude_id: int | None = None,
    ) -> None:
        stmt = select(File.id).where(
            File.user_id == user_id,
            File.parent_id == parent_id,
            File.name == name,
            File.is_deleted == False,
        )
        if exclude_id is not None:
            stmt = stmt.where(File.id != exclude_id)
        exists = (await db.exec(stmt)).first()
        if exists:
            raise NameConflict("已存在同名文件或目录")

    @classmethod
    async def _find_active_by_name(
        cls,
        db: AsyncSession,
        user_id: int,
        parent_id: int | None,
        name: str,
    ) -> File | None:
        stmt = select(File).where(
            File.user_id == user_id,
            File.parent_id == parent_id,
            File.name == name,
            File.is_deleted == False,
        )
        return (await db.exec(stmt)).first()

    @classmethod
    async def _generate_unique_name(
        cls,
        db: AsyncSession,
        user_id: int,
        parent_id: int | None,
        base_name: str,
    ) -> str:
        stem = base_name
        suffix = " (恢复)"
        if "." in base_name:
            parts = base_name.rsplit(".", 1)
            stem = parts[0]
            ext = "." + parts[1]
        else:
            ext = ""
        candidate = base_name
        for index in range(1, 1000):
            exists = await cls._find_active_by_name(db, user_id, parent_id, candidate)
            if not exists:
                return candidate
            candidate = f"{stem}{suffix}{index}{ext}"
        raise NameConflict("恢复失败：重名过多")

    @staticmethod
    def _ensure_zip_extension(name: str) -> str:
        return ensure_name(name if name.lower().endswith(".zip") else f"{name}.zip")

    @classmethod
    async def _generate_unique_name_with_suffix(
        cls,
        db: AsyncSession,
        user_id: int,
        parent_id: int | None,
        base_name: str,
        *,
        suffix: str,
        conflict_error: Exception,
    ) -> str:
        candidate = base_name
        exists = await cls._find_active_by_name(db, user_id, parent_id, candidate)
        if not exists:
            return candidate

        if "." in base_name:
            stem, ext_part = base_name.rsplit(".", 1)
            ext = f".{ext_part}"
        else:
            stem = base_name
            ext = ""

        for index in range(1, 1000):
            candidate = ensure_name(f"{stem}{suffix}{index}{ext}")
            exists = await cls._find_active_by_name(db, user_id, parent_id, candidate)
            if not exists:
                return candidate
        raise conflict_error

    @staticmethod
    def _dedupe_keep_order(values: list[int]) -> list[int]:
        unique_values: list[int] = []
        seen: set[int] = set()
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            unique_values.append(value)
        return unique_values

    @classmethod
    def _storage_path_for(cls, user_id: int, parent: File | None, name: str) -> str:
        return build_storage_path(
            user_id, parent.storage_path if parent else None, name
        )

    @classmethod
    async def get_entry(cls, db: AsyncSession, user_id: int, file_id: int) -> File:
        """
        获取单个文件或目录的元数据。
        仅允许访问未删除条目。
        权限由调用方完成，不在此重复鉴权。
        若不存在会抛出 ServiceException。
        并发安全：只读不修改状态。
        性能：单条查询，开销可控。
        返回：File 模型实例。
        用途：供 controller 获取详情。
        """
        return await cls._get_active_file(db, user_id, file_id)

    @classmethod
    @audited(
        "MKDIR",
        resource_type=lambda *args, **kwargs: _audit_resource_type_from_entry(
            kwargs.get("result")
        ),
        extractors=[_extract_from_result],
        auto_commit=True,
    )
    async def create_dir(
        cls,
        db: AsyncSession,
        user_id: int,
        parent_id: int | None,
        name: str,
        commit: bool = True,
    ) -> File:
        """
        创建目录并写入 DB 索引。
        parent_id 为空表示创建在用户根目录。
        name 会进行规范化与非法字符过滤。
        依赖唯一约束保证同级不重名。
        目录创建由存储后端执行，避免控制层直 I/O。
        若 DB 写入失败会回滚并清理目录。
        并发：同名竞争会抛出已存在错误。
        返回：新目录条目。
        """
        safe_name = ensure_name(name)
        parent = None
        if parent_id is not None:
            parent = await cls._get_active_dir(db, user_id, parent_id)
        await cls._ensure_unique_name(db, user_id, parent_id, safe_name)
        storage = await cls.get_default_storage(db)
        storage_path = cls._storage_path_for(user_id, parent, safe_name)
        storage_path_hash = cls._hash_storage_path(storage_path)
        backend = get_storage_backend(storage)

        try:
            # 先创建物理目录，确保路径有效且可写。
            backend.ensure_dir(storage_path)
        except Exception as exc:
            raise BadRequestException(str(exc)) from exc

        entry = File(
            user_id=user_id,
            parent_id=parent_id,
            name=safe_name,
            is_dir=True,
            size=0,
            mime_type=None,
            etag=uuid4().hex,
            storage_id=storage.id,
            storage_path=storage_path,
            storage_path_hash=storage_path_hash,
            content_hash=None,
            is_deleted=False,
            deleted_at=None,
        )
        db.add(entry)
        try:
            if commit:
                await db.commit()
            else:
                await db.flush()
        except IntegrityError as exc:
            await db.rollback()
            try:
                await backend.delete(storage_path, is_dir=True)
            except Exception:
                pass
            raise NameConflict("目录已存在") from exc
        await db.refresh(entry)
        return entry

    @classmethod
    async def upload_file(
        cls,
        db: AsyncSession,
        user_id: int,
        parent_id: int | None,
        name: str | None,
        upload: UploadFile,
        overwrite: bool = False,
        commit: bool = True,
    ) -> File:
        """
        单文件上传的便捷入口。
        内部复用分片上传流程，保证一致性。
        overwrite 为 False 时遇到重名会报错。
        数据写入先落临时分片，再 finalize 合并。
        幂等：同请求可安全重试初始化步骤。
        权限由调用方校验，不在此重复鉴权。
        失败会清理会话目录，避免残留。
        返回：创建的 File 记录。
        """
        if not upload.filename and not name:
            raise InvalidFileName("文件名不能为空")
        safe_name = ensure_name(name or upload.filename or "")
        await cls._prepare_upload_target(db, user_id, parent_id, safe_name, overwrite)
        storage = await cls.get_default_storage(db)
        backend = get_storage_backend(storage)
        upload_id = cls._make_upload_id(1)
        backend.ensure_upload_session(user_id, upload_id)
        try:
            size = await cls._with_upload_limit(
                user_id,
                db,
                backend.write_upload_part(user_id, upload_id, 1, upload),
            )
            max_size = await cls._upload_max_size_bytes(db)
            if max_size and size > max_size:
                backend.delete_upload_session(user_id, upload_id)
                raise PayloadTooLarge("文件大小超过上传限制")
            entry = await cls.finalize_upload(
                db=db,
                redis=get_async_redis(),
                user_id=user_id,
                upload_id=upload_id,
                parent_id=parent_id,
                name=safe_name,
                overwrite=overwrite,
                mime_type=upload.content_type,
                total_parts=1,
                commit=commit,
            )
            return entry
        finally:
            await upload.close()

    @classmethod
    async def list_dir(
        cls,
        db: AsyncSession,
        user_id: int,
        parent_id: int | None,
        page: int = 1,
        page_size: int = 200,
        order: str = "name",
    ) -> tuple[list[File], int]:
        """
        列出指定 parent_id 下的子项。
        只查询 DB 索引，不做磁盘遍历。
        order 仅支持 name/updated_at。
        page 与 page_size 做合法性校验。
        幂等：相同参数返回一致排序。
        并发安全：只读操作不修改状态。
        性能：分页查询避免全量加载。
        返回：文件列表与总数。
        """
        if page <= 0:
            raise InvalidPage()
        if page_size <= 0 or page_size > 500:
            raise InvalidPageSize()
        stmt = select(File).where(
            File.user_id == user_id,
            File.parent_id == parent_id,
            File.is_deleted == False,
        )
        count_stmt = select(func.count()).where(
            File.user_id == user_id,
            File.parent_id == parent_id,
            File.is_deleted == False,
        )
        if order == "updated_at":
            stmt = stmt.order_by(File.is_dir.desc(), File.updated_at.desc())
        else:
            stmt = stmt.order_by(File.is_dir.desc(), File.name.asc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        items = (await db.exec(stmt)).all()
        total = (await db.exec(count_stmt)).one()
        return items, int(total or 0)

    @classmethod
    async def list_dir_cursor(
        cls,
        db: AsyncSession,
        user_id: int,
        parent_id: int | None,
        cursor: int = 0,
        limit: int = 200,
        order: str = "name",
    ) -> tuple[list[File], int, int | None]:
        if limit <= 0 or limit > 500:
            raise InvalidPageSize()
        stmt = select(File).where(
            File.user_id == user_id,
            File.parent_id == parent_id,
            File.is_deleted == False,
        )
        count_stmt = select(func.count()).where(
            File.user_id == user_id,
            File.parent_id == parent_id,
            File.is_deleted == False,
        )
        if order == "updated_at":
            stmt = stmt.order_by(File.is_dir.desc(), File.updated_at.desc())
        else:
            stmt = stmt.order_by(File.is_dir.desc(), File.name.asc())
        stmt = stmt.offset(max(cursor, 0)).limit(limit)
        items = (await db.exec(stmt)).all()
        total = int((await db.exec(count_stmt)).one() or 0)
        next_cursor = cursor + limit if cursor + limit < total else None
        return items, total, next_cursor

    @classmethod
    async def search_by_name_cursor(
        cls,
        db: AsyncSession,
        user_id: int,
        keyword: str,
        cursor: int = 0,
        limit: int = 200,
        order: str = "name",
    ) -> tuple[list[File], int, int | None]:
        if limit <= 0 or limit > 500:
            raise InvalidPageSize()
        term = (keyword or "").strip()
        if not term:
            return [], 0, None
        stmt = select(File).where(
            File.user_id == user_id,
            File.is_deleted == False,
            File.name.contains(term),
        )
        count_stmt = select(func.count()).where(
            File.user_id == user_id,
            File.is_deleted == False,
            File.name.contains(term),
        )
        if order == "updated_at":
            stmt = stmt.order_by(File.is_dir.desc(), File.updated_at.desc(), File.id.desc())
        else:
            stmt = stmt.order_by(File.is_dir.desc(), File.name.asc(), File.id.asc())
        stmt = stmt.offset(max(cursor, 0)).limit(limit)
        items = (await db.exec(stmt)).all()
        total = int((await db.exec(count_stmt)).one() or 0)
        next_cursor = cursor + limit if cursor + limit < total else None
        return items, total, next_cursor

    @classmethod
    async def soft_delete(
        cls,
        db: AsyncSession,
        user_id: int,
        file_id: int,
        commit: bool = True,
    ) -> list[int]:
        """
        软删除文件或目录，进入回收站。
        目录会级联软删子孙节点。
        物理文件统一移动到回收站路径。
        软删除标记用于唯一约束放行重名。
        并发：依赖 DB 与存储原子移动。
        失败会抛出异常并停止操作。
        性能：目录规模决定递归深度。
        返回：被软删的文件 ID 列表。
        """
        target = await cls._get_active_file(db, user_id, file_id)
        ids = [target.id]
        descendants: list[File] = []
        if target.is_dir:
            ids.extend(
                await cls._collect_descendants(
                    db, user_id, [target.id], include_deleted=False
                )
            )
            descendants = await cls._collect_descendant_entries(
                db, user_id, [target.id], include_deleted=False
            )
        entries = [target, *descendants]
        now = datetime.now()
        deleted_at_token = f"{int(now.timestamp() * 1000)}_{uuid4().hex[:8]}"
        storage = await cls._get_storage_by_id(db, target.storage_id)
        backend = get_storage_backend(storage)
        old_path = target.storage_path
        trash_path = build_trash_path(user_id, target.id, target.name, deleted_at_token)
        # 先移动真实路径，避免 DB 已删除但文件仍在原位。
        await backend.move(old_path, trash_path)
        old_prefix = old_path.rstrip("/")
        new_prefix = trash_path.rstrip("/")
        for entry in entries:
            if entry.id == target.id:
                entry.storage_path = trash_path
            else:
                if entry.storage_path.startswith(old_prefix + "/"):
                    entry.storage_path = (
                        new_prefix + entry.storage_path[len(old_prefix) :]
                    )
            entry.storage_path_hash = cls._hash_storage_path(entry.storage_path)
            entry.is_deleted = True
            entry.deleted_at = now
        if commit:
            await db.commit()
        else:
            await db.flush()
        return ids

    @classmethod
    @audited(
        "DELETE",
        resource_type=lambda *args, **kwargs: _audit_resource_type_from_entry(
            kwargs.get("result")
        ),
        extractors=[_extract_from_result],
        auto_commit=True,
    )
    async def delete_entry(
        cls,
        db: AsyncSession,
        user_id: int,
        file_id: int,
        commit: bool = True,
    ) -> File:
        target = await cls._get_active_file(db, user_id, file_id)
        await cls.soft_delete(db, user_id, file_id, commit=commit)
        return target

    @classmethod
    async def restore(cls, db: AsyncSession, user_id: int, file_id: int) -> File:
        """
        从回收站恢复文件或目录。
        若同名冲突会自动生成新名称。
        物理路径会从回收站移动回原位置。
        目录恢复会级联子孙节点状态。
        并发：依赖唯一约束检测冲突。
        失败时会尝试回滚存储路径。
        性能：目录恢复可能更新多条记录。
        返回：恢复后的条目。
        """
        stmt = select(File).where(
            File.id == file_id,
            File.user_id == user_id,
            File.is_deleted == True,
        )
        target = (await db.exec(stmt)).first()
        if not target:
            raise FileNotFound("文件或目录不存在")
        parent = None
        if target.parent_id is not None:
            parent_stmt = select(File).where(
                File.id == target.parent_id,
                File.user_id == user_id,
            )
            parent = (await db.exec(parent_stmt)).first()
            if not parent:
                raise RestoreParentMissing()
            if parent.is_deleted:
                raise RestoreParentDeleted()
            if not parent.is_dir:
                raise ParentNotDirectory()
        try:
            await cls._ensure_unique_name(
                db, user_id, target.parent_id, target.name, exclude_id=target.id
            )
            restore_name = target.name
        except NameConflict:
            restore_name = await cls._generate_unique_name(
                db, user_id, target.parent_id, target.name
            )
            target.name = restore_name
        storage = await cls._get_storage_by_id(db, target.storage_id)
        backend = get_storage_backend(storage)
        old_path = target.storage_path
        new_path = cls._storage_path_for(user_id, parent, restore_name)
        moved = False
        if old_path != new_path:
            await backend.move(old_path, new_path)
            moved = True
            # 清理回收站空目录，避免残留 时间戳_id 空目录。
            if hasattr(backend, "cleanup_empty_parents"):
                try:
                    trash_root = f".trash/{user_id}"
                    backend.cleanup_empty_parents(old_path, trash_root)
                except Exception:
                    pass
        descendants: list[File] = []
        if target.is_dir:
            descendants = await cls._collect_descendant_entries(
                db, user_id, [target.id], include_deleted=True
            )
        old_prefix = old_path.rstrip("/")
        new_prefix = new_path.rstrip("/")
        for entry in [target, *descendants]:
            if entry.id == target.id:
                entry.storage_path = new_path
            else:
                if entry.storage_path.startswith(old_prefix + "/"):
                    entry.storage_path = (
                        new_prefix + entry.storage_path[len(old_prefix) :]
                    )
            entry.storage_path_hash = cls._hash_storage_path(entry.storage_path)
            entry.is_deleted = False
            entry.deleted_at = None
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            if moved:
                try:
                    await backend.move(new_path, old_path)
                except Exception:
                    pass
            raise NameConflict("同名文件或目录已存在") from exc
        await db.refresh(target)
        return target

    @classmethod
    @audited(
        "MOVE",
        resource_type=lambda *args, **kwargs: _audit_resource_type_from_entry(
            kwargs.get("result")
        ),
        extractors=[_extract_from_result],
        auto_commit=True,
    )
    async def move(
        cls,
        db: AsyncSession,
        user_id: int,
        file_id: int,
        target_parent_id: int | None,
        new_name: str | None = None,
        commit: bool = True,
    ) -> File:
        """
        移动文件或目录到新的父目录。
        目录移动时会同步更新子孙 storage_path。
        目标目录必须与源存储一致。
        不允许移动到自身或其子孙目录。
        并发下通过唯一约束检测重名冲突。
        若移动失败会回滚存储路径。
        性能：目录更新成本与深度相关。
        返回：更新后的条目。
        """
        target = await cls._get_active_file(db, user_id, file_id)
        if target_parent_id == target.id:
            raise MoveToSelf()
        parent = None
        if target_parent_id is not None:
            parent = await cls._get_active_dir(db, user_id, target_parent_id)
        if parent and parent.storage_id != target.storage_id:
            raise StorageMismatch()
        if target.is_dir and target_parent_id is not None:
            if await cls._is_descendant(db, user_id, target_parent_id, target.id):
                raise MoveToDescendant()
        safe_name = ensure_name(new_name or target.name)
        await cls._ensure_unique_name(
            db, user_id, target_parent_id, safe_name, exclude_id=target.id
        )
        storage = await cls.get_default_storage(db)
        if storage.id != target.storage_id:
            storage = await cls._get_storage_by_id(db, target.storage_id)
        backend = get_storage_backend(storage)
        old_path = target.storage_path
        new_path = cls._storage_path_for(user_id, parent, safe_name)
        if old_path == new_path and target.parent_id == target_parent_id:
            return target
        # 先移动物理路径，确保 DB 与存储一致。
        await backend.move(old_path, new_path)

        descendants: list[File] = []
        if target.is_dir:
            descendants = await cls._collect_descendant_entries(
                db, user_id, [target.id]
            )
        old_prefix = old_path.rstrip("/")
        new_prefix = new_path.rstrip("/")
        if target.is_dir:
            for child in descendants:
                if child.storage_path.startswith(old_prefix + "/"):
                    child.storage_path = (
                        new_prefix + child.storage_path[len(old_prefix) :]
                    )
                    child.storage_path_hash = cls._hash_storage_path(child.storage_path)

        target.parent_id = target_parent_id
        target.name = safe_name
        target.storage_path = new_path
        target.storage_path_hash = cls._hash_storage_path(new_path)
        try:
            if commit:
                await db.commit()
            else:
                await db.flush()
        except IntegrityError as exc:
            await db.rollback()
            try:
                await backend.move(new_path, old_path)
            except Exception:
                pass
            raise NameConflict("目标名称冲突") from exc
        await db.refresh(target)
        return target

    @classmethod
    @audited(
        "RENAME",
        resource_type=lambda *args, **kwargs: _audit_resource_type_from_entry(
            kwargs.get("result")
        ),
        extractors=[_extract_from_result],
        auto_commit=True,
    )
    async def rename(
        cls,
        db: AsyncSession,
        user_id: int,
        file_id: int,
        new_name: str,
        commit: bool = True,
    ) -> File:
        """
        重命名文件或目录。
        内部复用 move 逻辑保持一致性。
        仅修改名称，不改变 parent_id。
        并发下若重名会抛出错误。
        目录重命名会更新子孙路径。
        性能：目录越大更新越多。
        错误：透传 ServiceException。
        返回：更新后的条目。
        """
        target = await cls._get_active_file(db, user_id, file_id)
        return await cls.move(
            db=db,
            user_id=user_id,
            file_id=file_id,
            target_parent_id=target.parent_id,
            new_name=new_name,
            commit=commit,
        )

    @classmethod
    async def refresh_used_space(cls, db: AsyncSession, user_id: int) -> int:
        """
        重新计算并刷新用户已用空间。
        只统计未删除文件的 size 总和。
        结果写回用户表用于配额展示。
        权限由调用方校验，不在此重复。
        并发：多次刷新以最后一次为准。
        性能：聚合查询，成本可控。
        用途：上传/删除/恢复后调用。
        返回：最新已用空间数值。
        """
        stmt = select(func.coalesce(func.sum(File.size), 0)).where(
            File.user_id == user_id,
            File.is_deleted == False,
            File.is_dir == False,
        )
        total = int((await db.exec(stmt)).one() or 0)
        user = await user_crud.get_by_id(db, user_id)
        if user:
            user.used_space = total
            await db.commit()
            await db.refresh(user)
        return total

    @classmethod
    async def _collect_descendants(
        cls,
        db: AsyncSession,
        user_id: int,
        parent_ids: list[int],
        include_deleted: bool = False,
    ) -> list[int]:
        ids: list[int] = []
        queue = list(parent_ids)
        while queue:
            stmt = select(File.id).where(
                File.user_id == user_id,
                File.parent_id.in_(queue),
            )
            if not include_deleted:
                stmt = stmt.where(File.is_deleted == False)
            children = (await db.exec(stmt)).all()
            if not children:
                break
            ids.extend(children)
            queue = children
        return ids

    @classmethod
    async def _collect_descendant_entries(
        cls,
        db: AsyncSession,
        user_id: int,
        parent_ids: list[int],
        include_deleted: bool = False,
    ) -> list[File]:
        items: list[File] = []
        queue = list(parent_ids)
        while queue:
            stmt = select(File).where(
                File.user_id == user_id,
                File.parent_id.in_(queue),
            )
            if not include_deleted:
                stmt = stmt.where(File.is_deleted == False)
            children = (await db.exec(stmt)).all()
            if not children:
                break
            items.extend(children)
            queue = [child.id for child in children]
        return items

    @classmethod
    async def _is_descendant(
        cls, db: AsyncSession, user_id: int, node_id: int, ancestor_id: int
    ) -> bool:
        current_id = node_id
        while current_id is not None:
            stmt = select(File.parent_id).where(
                File.id == current_id,
                File.user_id == user_id,
                File.is_deleted == False,
            )
            parent_id = (await db.exec(stmt)).first()
            if parent_id is None:
                break
            if parent_id == ancestor_id:
                return True
            current_id = parent_id
        return False

    @classmethod
    async def _prepare_upload_target(
        cls,
        db: AsyncSession,
        user_id: int,
        parent_id: int | None,
        safe_name: str,
        overwrite: bool,
    ) -> tuple[File | None, Storage, str]:
        parent = None
        if parent_id is not None:
            parent = await cls._get_active_dir(db, user_id, parent_id)
        existing = await cls._find_active_by_name(db, user_id, parent_id, safe_name)
        if existing:
            if not overwrite:
                raise NameConflict("文件已存在")
            if existing.is_dir:
                raise NameConflict("同名目录已存在")
            await cls.soft_delete(db, user_id, existing.id)
        else:
            await cls._ensure_unique_name(db, user_id, parent_id, safe_name)
        storage = await cls.get_default_storage(db)
        if parent and parent.storage_id != storage.id:
            raise StorageMismatch("父目录存储不一致")
        storage_path = cls._storage_path_for(user_id, parent, safe_name)
        return parent, storage, storage_path

    @classmethod
    async def init_upload_session(
        cls,
        db: AsyncSession,
        redis,
        user_id: int,
        parent_id: int | None,
        name: str,
        size: int,
        part_size: int,
        overwrite: bool,
    ) -> dict:
        """
        初始化分片上传会话。
        会话状态由文件系统目录表达。
        先校验父目录与同名冲突。
        仅生成 upload_id，不写入 DB。
        total_parts 用于校验完整性。
        幂等：重复初始化会生成新会话。
        性能：仅创建目录，开销小。
        返回：upload_id 与过期信息。
        """
        if size < 0:
            raise BadRequestException("文件大小不合法")
        part_size = await cls._upload_chunk_size_bytes(db)
        max_size = await cls._upload_max_size_bytes(db)
        if max_size and size > max_size:
            raise PayloadTooLarge("文件大小超过上传限制")
        safe_name = ensure_name(name)
        await cls._prepare_upload_target(db, user_id, parent_id, safe_name, overwrite)
        total_parts = max(1, (size + part_size - 1) // part_size)
        upload_id = cls._make_upload_id(total_parts)
        await cls._reserve_upload_quota(
            db=db,
            redis=redis,
            user_id=user_id,
            upload_id=upload_id,
            reserved_bytes=size,
        )
        storage = await cls.get_default_storage(db)
        backend = get_storage_backend(storage)
        try:
            backend.ensure_upload_session(user_id, upload_id)
        except Exception:
            await cls._release_upload_reservation(redis, user_id, upload_id)
            raise
        return {
            "upload_id": upload_id,
            "part_size": part_size,
            "total_parts": total_parts,
            "expires_in": cls._session_ttl(),
        }

    @classmethod
    async def upload_part(
        cls,
        db: AsyncSession,
        user_id: int,
        upload_id: str,
        part_number: int,
        upload: UploadFile,
    ) -> int:
        """
        写入指定分片。
        分片写入采用临时文件 + 原子替换。
        若分片已存在则校验大小以保证幂等。
        每次上传会更新会话目录 mtime。
        不触碰数据库，避免状态分裂。
        并发：不同分片可并行上传。
        错误：冲突或会话不存在时抛错。
        返回：写入分片大小。
        """
        if part_number <= 0:
            raise InvalidPartNumber()
        total_parts = cls._parse_upload_id(upload_id)
        if not total_parts:
            raise InvalidUploadId()
        if part_number > total_parts:
            raise InvalidPartNumber("分片编号超出范围")
        storage = await cls.get_default_storage(db)
        backend = get_storage_backend(storage)
        state = backend.get_upload_session_state(user_id, upload_id)
        if not state.get("exists"):
            raise UploadSessionNotFound()
        if state.get("done"):
            raise UploadSessionCompleted()
        if state.get("locked"):
            raise UploadFinalizing()
        try:
            size = await cls._with_upload_limit(
                user_id,
                db,
                backend.write_upload_part(user_id, upload_id, part_number, upload),
            )
            await cls._touch_upload_reservation(redis=get_async_redis(), user_id=user_id, upload_id=upload_id)
            return size
        finally:
            await upload.close()

    @classmethod
    async def get_upload_status(
        cls,
        db: AsyncSession,
        user_id: int,
        upload_id: str,
    ) -> dict:
        """
        获取上传会话状态与分片信息。
        状态由 .lock/.done 与目录存在性推断。
        不读取数据库，避免状态不一致。
        missing_parts 由 total_parts 计算得出。
        expires_in 由 mtime 与 TTL 计算。
        并发安全：只读访问会话目录。
        会话不存在时抛出明确错误。
        返回：状态与分片统计。
        """
        total_parts = cls._parse_upload_id(upload_id)
        if not total_parts:
            raise InvalidTotalParts("无法解析分片总数")
        storage = await cls.get_default_storage(db)
        backend = get_storage_backend(storage)
        state = backend.get_upload_session_state(user_id, upload_id)
        if not state.get("exists"):
            raise UploadSessionNotFound()
        await cls._touch_upload_reservation(redis=get_async_redis(), user_id=user_id, upload_id=upload_id)
        parts = state.get("parts") or []
        uploaded_set = set(parts)
        missing = [idx for idx in range(1, total_parts + 1) if idx not in uploaded_set]
        status = "UPLOADING"
        if state.get("locked"):
            status = "FINALIZING"
        if state.get("done"):
            status = "DONE"
        mtime = float(state.get("mtime") or 0)
        expires_in = max(
            0, int(mtime + cls._session_ttl() - datetime.now().timestamp())
        )
        return {
            "status": status,
            "total_parts": total_parts,
            "uploaded_parts": parts,
            "missing_parts": missing,
            "uploaded_bytes": int(state.get("uploaded_bytes") or 0),
            "expires_in": expires_in,
        }

    @classmethod
    @audited(
        "UPLOAD",
        resource_type=lambda *args, **kwargs: _audit_resource_type_from_entry(
            kwargs.get("result")
        ),
        extractors=[_extract_from_result],
        auto_commit=True,
    )
    async def finalize_upload(
        cls,
        db: AsyncSession,
        redis,
        user_id: int,
        upload_id: str,
        parent_id: int | None,
        name: str,
        overwrite: bool,
        mime_type: str | None = None,
        total_parts: int | None = None,
        commit: bool = True,
    ) -> File:
        """
        合并分片并创建最终文件条目。
        通过 .lock 文件保证 finalize 并发安全。
        若 .done 已存在则直接返回已完成文件。
        合并完成后进行原子替换与 fsync。
        DB 写入失败会回滚并清理临时文件。
        total_parts 支持从 upload_id 推断。
        幂等：重复 finalize 会返回相同结果。
        返回：创建的 File 记录。
        """
        safe_name = ensure_name(name)
        total = total_parts or cls._parse_upload_id(upload_id)
        if not total:
            raise InvalidTotalParts("分片总数缺失")
        storage = await cls.get_default_storage(db)
        backend = get_storage_backend(storage)
        state = backend.get_upload_session_state(user_id, upload_id)
        if not state.get("exists"):
            raise UploadSessionNotFound()
        if state.get("done"):
            await cls._release_upload_reservation(redis, user_id, upload_id)
            return await cls._get_active_file_by_path(db, user_id, parent_id, safe_name)
        _, storage, storage_path = await cls._prepare_upload_target(
            db, user_id, parent_id, safe_name, overwrite
        )
        # 通过独占锁避免并发 finalize 造成重复合并。
        if not backend.acquire_upload_lock(user_id, upload_id):
            raise UploadFinalizing()
        try:
            parts = state.get("parts") or []
            uploaded = set(parts)
            missing = [idx for idx in range(1, total + 1) if idx not in uploaded]
            if missing:
                raise ChunkIncomplete()
            # 合并分片时顺序读取，保持内存稳定。
            size, digest = await cls._with_upload_limit(
                user_id,
                db,
                backend.merge_upload_parts(user_id, upload_id, total, storage_path),
            )
            try:
                reserved_bytes = await cls._get_upload_reserved_bytes(
                    redis,
                    user_id,
                    upload_id,
                )
                await cls._ensure_quota_available(
                    db,
                    user_id,
                    max(0, size - reserved_bytes),
                    exclude_upload_id=upload_id,
                )
            except Exception:
                try:
                    await backend.delete(storage_path, is_dir=False)
                except Exception:
                    pass
                raise
            entry = File(
                user_id=user_id,
                parent_id=parent_id,
                name=safe_name,
                is_dir=False,
                size=size,
                mime_type=mime_type or mimetypes.guess_type(safe_name)[0],
                etag=digest,
                storage_id=storage.id,
                storage_path=storage_path,
                storage_path_hash=cls._hash_storage_path(storage_path),
                content_hash=digest,
                is_deleted=False,
                deleted_at=None,
            )
            db.add(entry)
            try:
                if commit:
                    await db.commit()
                else:
                    await db.flush()
            except IntegrityError as exc:
                await db.rollback()
                try:
                    await backend.delete(storage_path, is_dir=False)
                except Exception:
                    pass
                raise NameConflict("文件已存在") from exc
            await db.refresh(entry)
            backend.mark_upload_done(user_id, upload_id)
            await cls._release_upload_reservation(redis, user_id, upload_id)
            return entry
        finally:
            backend.release_upload_lock(user_id, upload_id)

    @classmethod
    async def cancel_upload(
        cls,
        db: AsyncSession,
        redis,
        user_id: int,
        upload_id: str,
    ) -> None:
        """
        取消上传会话并删除临时目录。
        若会话处于 finalize 锁定状态会报错。
        不操作数据库，避免误删正式文件。
        幂等：会话不存在直接返回。
        适用于用户主动取消上传。
        性能：删除单个目录。
        错误：锁冲突时提示稍后重试。
        返回：None。
        """
        storage = await cls.get_default_storage(db)
        backend = get_storage_backend(storage)
        state = backend.get_upload_session_state(user_id, upload_id)
        if not state.get("exists"):
            await cls._release_upload_reservation(redis, user_id, upload_id)
            return
        if state.get("locked"):
            raise UploadFinalizing()
        backend.delete_upload_session(user_id, upload_id)
        await cls._release_upload_reservation(redis, user_id, upload_id)

    @classmethod
    async def gc_uploads(
        cls,
        db: AsyncSession,
        redis,
        dry_run: bool = False,
    ) -> dict:
        """
        执行上传会话 GC 清理。
        仅依赖文件系统目录 mtime 判断。
        dry_run 为 True 时仅统计不删除。
        会跳过锁定中的会话以避免并发冲突。
        stale lock 会记录日志并删除。
        权限由调用方校验（管理端接口）。
        性能：扫描上传根目录。
        返回：扫描与删除统计信息。
        """
        storage = await cls.get_default_storage(db)
        backend = get_storage_backend(storage)
        result = backend.gc_upload_sessions(
            session_ttl=cls._session_ttl(),
            done_ttl=cls._done_ttl(),
            dry_run=dry_run,
        )
        if not dry_run:
            async for key in redis.scan_iter(match="disk:quota:reservation_index:*", count=100):
                user_id = cls._parse_positive_int(str(key).rsplit(":", 1)[-1])
                if user_id <= 0:
                    continue
                upload_ids = await redis.smembers(key)
                if not upload_ids:
                    continue
                for raw_upload_id in upload_ids:
                    upload_id = str(raw_upload_id)
                    state = backend.get_upload_session_state(user_id, upload_id)
                    if not state.get("exists"):
                        await cls._release_upload_reservation(redis, user_id, upload_id)
                await cls._sum_upload_reservations(redis, user_id)
        return result

    @classmethod
    async def _get_active_file_by_path(
        cls, db: AsyncSession, user_id: int, parent_id: int | None, name: str
    ) -> File:
        stmt = select(File).where(
            File.user_id == user_id,
            File.parent_id == parent_id,
            File.name == name,
            File.is_deleted == False,
        )
        entry = (await db.exec(stmt)).first()
        if not entry:
            raise FileNotFound()
        return entry

    @staticmethod
    def _decode_redis_hash(data: dict) -> dict:
        decoded: dict[str, str] = {}
        for key, value in data.items():
            if isinstance(key, bytes):
                key = key.decode()
            if isinstance(value, bytes):
                value = value.decode()
            decoded[str(key)] = str(value)
        return decoded

    @classmethod
    async def read_text_file(cls, db: AsyncSession, file_id: int, user_id: int) -> dict:
        """
        读取文本文件内容。
        仅允许读取未删除文件。
        内容会以 UTF-8 读取并替换非法字符。
        权限由调用方校验，不在此重复。
        并发安全：只读操作不修改状态。
        性能：读取整文件，适合小文本。
        返回：文本内容与元信息。
        错误：文件不存在或为目录。
        """
        file = await cls._get_active_file(db, user_id, file_id)
        if file.is_dir:
            raise InvalidTargetType()
        storage = await cls._get_storage_by_id(db, file.storage_id)
        backend = get_storage_backend(storage)
        content, size, modified_time = await backend.read_text(file.storage_path)
        return {
            "file_id": file.id,
            "content": content,
            "size": size,
            "modified_time": modified_time,
        }

    @staticmethod
    def build_download_response(
        request: Request,
        file_path: Path,
        filename: str,
        inline: bool,
        background: BackgroundTask | None = None,
    ):
        """
        构建文件下载或预览响应。
        使用 Range 支持与标准头部输出。
        inline 控制 Content-Disposition 行为。
        background 可用于清理临时文件。
        不读取文件内容，交由响应层流式输出。
        幂等：同参数返回一致 header。
        性能：响应层按需读取文件。
        返回：StreamingResponse 或 FileResponse。
        """
        if inline:
            media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            return _build_inline_response(
                request=request,
                file_path=file_path,
                filename=filename,
                media_type=media_type,
                background=background,
            )
        return _build_file_response(
            request=request,
            file_path=file_path,
            filename=filename,
            background=background,
        )

    @classmethod
    async def issue_download_url(
        cls,
        request: Request,
        db: AsyncSession,
        file_id: int,
        user_id: int,
        redis,
    ) -> dict:
        """
        签发下载 URL（带 token）用于下载。
        仅允许已登录用户调用，依赖 JWT 鉴权。
        token 2 小时过期，存入 Redis 以便失效控制。
        token 强绑定 file_id，避免跨资源盗用。
        token 绑定 IP/UA，降低链接被转发滥用风险。
        安全点：不把 JWT 放到 URL 中，降低泄露风险。
        权限假设：调用方已通过下载权限校验。
        并发：可并行签发多个 URL。
        性能：一次 DB 查询 + Redis 写入。
        返回：完整下载 URL 与 expires_in。
        """
        entry = await cls._get_active_file(db, user_id, file_id)
        ttl = await cls._download_token_ttl(db)
        now = int(time.time())
        token = secrets.token_urlsafe(32)
        client_ip = cls._extract_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        payload = {
            "rid": entry.id,
            "act": "download",
            "uid": user_id,
            "created_at": now,
            "expires_at": now + ttl,
            "filename_hint": entry.name,
            "ip": client_ip,
            "ua": user_agent,
        }
        key = f"dl:tok:{token}"
        # 使用 TTL 控制有效期，避免长期可用的下载链接。
        await redis.setex(key, ttl, json.dumps(payload, ensure_ascii=False))
        prefix = settings.APP_API_PREFIX or "/api/v1"
        # 返回相对 URL，避免在多环境下拼接错误域名。
        url = f"{prefix}/files/{entry.id}/download?token={token}"
        return {"url": url, "expires_in": ttl}

    @classmethod
    async def issue_preview_url(
        cls,
        request: Request,
        db: AsyncSession,
        file_id: int,
        user_id: int,
        redis,
    ) -> dict:
        """
        签发预览 URL（带 token）。
        仅用于视频等需要 Range 的预览场景。
        token 3 小时过期，存入 Redis。
        act=preview，用于与下载 token 区分。
        token 强绑定 file_id，并绑定 IP/UA。
        安全点：不把 JWT 放到 URL 中。
        并发：可并行签发多个 URL。
        性能：一次 DB 查询 + Redis 写入。
        返回：相对预览 URL 与 expires_in。
        """
        entry = await cls._get_active_file(db, user_id, file_id)
        if entry.is_dir:
            raise PreviewNotSupported()
        ttl = await cls._preview_token_ttl(db)
        now = int(time.time())
        token = secrets.token_urlsafe(32)
        client_ip = cls._extract_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        payload = {
            "rid": entry.id,
            "act": "preview",
            "uid": user_id,
            "created_at": now,
            "expires_at": now + ttl,
            "filename_hint": entry.name,
            "ip": client_ip,
            "ua": user_agent,
        }
        key = f"dl:tok:{token}"
        await redis.setex(key, ttl, json.dumps(payload, ensure_ascii=False))
        prefix = settings.APP_API_PREFIX or "/api/v1"
        url = f"{prefix}/files/{entry.id}/preview?token={token}"
        return {"url": url, "expires_in": ttl}

    @classmethod
    async def verify_download_token(
        cls, request: Request, file_id: int, token: str, redis, action: str = "download"
    ) -> dict:
        """
        校验 token 并返回其 payload。
        token 必须存在且未过期（Redis TTL 控制）。
        act 必须匹配期望动作（download/preview）。
        rid 必须与 URL file_id 相同，强绑定资源。
        同时校验 IP/UA，降低链接被转发滥用风险。
        安全点：即便 token 存在也拒绝不匹配资源。
        并发：只读 Redis，不改变状态。
        性能：一次 Redis 读取与 JSON 解析。
        错误：失败时抛出 ServiceException。
        返回：payload 字典。
        """
        if not token:
            raise FileTokenInvalid("下载令牌无效")
        raw = await redis.get(f"dl:tok:{token}")
        if not raw:
            raise FileTokenExpired("下载令牌不存在或已过期")
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        try:
            payload = json.loads(raw)
        except Exception as exc:
            raise FileTokenInvalid("下载令牌解析失败") from exc
        if payload.get("act") != action:
            raise FileTokenInvalid("下载令牌类型错误")
        if int(payload.get("rid") or 0) != int(file_id):
            raise FileTokenInvalid("下载令牌与资源不匹配")
        expires_at = int(payload.get("expires_at") or 0)
        if expires_at and int(time.time()) > expires_at:
            raise FileTokenExpired("下载令牌已过期")
        if payload.get("ip") and payload.get("ip") != cls._extract_client_ip(request):
            raise FileTokenInvalid("下载令牌已失效")
        if payload.get("ua") and payload.get("ua") != request.headers.get(
            "user-agent", ""
        ):
            raise FileTokenInvalid("下载令牌已失效")
        return payload

    @classmethod
    @audited(
        "DOWNLOAD",
        resource_type=lambda *args, **kwargs: _audit_resource_type_from_entry(
            kwargs.get("result").entry if kwargs.get("result") else None
        ),
        extractors=[_extract_from_result],
        auto_commit=True,
    )
    async def download_direct(
        cls,
        request: Request,
        db: AsyncSession,
        file_id: int,
        user_id: int,
        disposition: str,
        commit: bool = False,
    ) -> DownloadResult:
        entry = await cls.get_entry(db=db, user_id=user_id, file_id=file_id)
        inline = disposition == "inline"
        if entry.is_dir:
            response = await cls.download_folder_zip_stream(
                request=request,
                db=db,
                root=entry,
                filename=f"{entry.name or 'root'}.zip",
            )
        else:
            file_path, filename, cleanup, _ = await cls.prepare_download(
                db, entry.id, user_id
            )
            response = cls.build_download_response(
                request=request,
                file_path=file_path,
                filename=filename,
                inline=inline,
                background=BackgroundTask(cls.cleanup_download_file, file_path)
                if cleanup
                else None,
            )
        return FileService.DownloadResult(response=response, entry=entry)

    @classmethod
    @audited(
        "DOWNLOAD",
        resource_type=None,
        extractors=[_extract_download],
        auto_commit=True,
    )
    async def download_file(
        cls,
        request: Request,
        db: AsyncSession,
        file_id: int,
        token: str,
        redis,
        commit: bool = False,
    ) -> Response:
        """
        通过下载 token 获取文件或目录。
        token 强绑定 file_id，且 2 小时过期。
        仍会用 token 内 uid 做一次权限校验，确保撤权生效。
        文件下载支持 Range；目录下载为流式 ZIP。
        安全点：不接受 JWT，避免 URL 外泄时暴露身份。
        并发：token 可复用，多次下载不失效。
        性能：文件为流式读取，内存占用稳定。
        返回：下载响应或 ZIP 流响应。
        """
        uid = None
        try:
            payload = await cls.verify_download_token(
                request, file_id, token, redis, "download"
            )
            uid = int(payload.get("uid") or 0)
            if uid <= 0:
                raise FileTokenInvalid("下载令牌无效")
            entry = await cls._get_active_file(db, uid, file_id)
            if entry.is_dir:
                filename = f"{entry.name or 'root'}.zip"
                response = await cls.download_folder_zip_stream(
                    request=request, db=db, root=entry, filename=filename
                )
            else:
                file_path, filename, cleanup, _ = await cls.prepare_download(db, entry.id, uid)
                background = BackgroundTask(_cleanup_abs_path, file_path) if cleanup else None
                response = cls.build_download_response(
                    request=request,
                    file_path=file_path,
                    filename=filename,
                    inline=False,
                    background=background,
                )
            return response
        except Exception as exc:
            raise

    @classmethod
    async def preview_file(
        cls,
        request: Request,
        db: AsyncSession,
        file_id: int,
        token: str,
        redis,
    ) -> Response:
        """
        通过预览 token 获取文件预览。
        token act=preview，TTL 3 小时。
        token 强绑定 file_id 与 IP/UA。
        仍基于 uid 做一次权限复核。
        预览支持 Range，便于视频在线播放。
        安全点：不接受 JWT，避免 URL 外泄时暴露身份。
        并发：token 可复用，多次预览不失效。
        性能：流式读取，内存占用稳定。
        返回：inline 预览响应。
        """
        payload = await cls.verify_download_token(
            request, file_id, token, redis, "preview"
        )
        uid = int(payload.get("uid") or 0)
        if uid <= 0:
            raise FileTokenInvalid("预览令牌无效")
        entry = await cls._get_active_file(db, uid, file_id)
        if entry.is_dir:
            raise PreviewNotSupported()
        file_path, filename, cleanup, _ = await cls.prepare_download(db, entry.id, uid)
        background = BackgroundTask(_cleanup_abs_path, file_path) if cleanup else None
        return cls.build_download_response(
            request=request,
            file_path=file_path,
            filename=filename,
            inline=True,
            background=background,
        )

    @classmethod
    async def download_folder_zip_stream(
        cls, request: Request, db: AsyncSession, root: File, filename: str
    ) -> StreamingResponse:
        """
        目录流式打包并下载。
        仅依赖 DB 索引获取子孙节点。
        客户端断开连接时尽快停止输出。
        不生成临时 zip 文件，避免磁盘占用。
        权限假设：调用方已校验访问权限。
        并发：读取过程中不持有全局锁。
        Range：不适用于 ZIP 流。
        返回：StreamingResponse。
        """
        # 统一入口，避免控制层直接依赖内部实现细节。
        return await cls.stream_zip_dir(
            request=request, db=db, root=root, filename=filename
        )

    @staticmethod
    def _extract_client_ip(request: Request) -> str:
        """
        提取请求来源 IP。
        优先读取 X-Forwarded-For 第一段。
        回退到 request.client.host。
        仅用于下载 token 绑定校验。
        并发：纯函数无状态。
        性能：字符串处理开销极小。
        返回：IP 字符串。
        """
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        ip = request.client.host if request.client else ""
        # # 兼容本地开发 IPv4/IPv6 回环地址差异，避免误判。
        # if ip in ("127.0.0.1", "::1"):
        #     return "localhost"
        return ip

    @staticmethod
    def cleanup_download_file(file_path: Path) -> None:
        _cleanup_abs_path(file_path)

    @staticmethod
    def _guess_preview_kind(entry: File) -> str:
        ext = PurePosixPath(entry.name or "").suffix.lower()
        if ext in {
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".webp",
            ".svg",
            ".heic",
            ".heif",
        }:
            return "image"
        if ext == ".pdf":
            return "pdf"
        if ext in {".mp4", ".mov", ".mkv", ".avi", ".flv", ".wmv", ".webm", ".m4v"}:
            return "video"
        mime_type = (entry.mime_type or "").lower()
        if mime_type.startswith("image/"):
            return "image"
        if mime_type.startswith("video/"):
            return "video"
        if mime_type == "application/pdf":
            return "pdf"
        return "other"

    @staticmethod
    def _normalize_thumbnail_size(value: int, default: int) -> int:
        if value <= 0:
            return default
        return max(16, min(2048, int(value)))

    @staticmethod
    def _thumbnail_media_type(fmt: str) -> str:
        normalized = (fmt or "webp").lower()
        if normalized in {"jpeg", "jpg"}:
            return "image/jpeg"
        if normalized == "png":
            return "image/png"
        return "image/webp"

    @staticmethod
    def _thumbnail_ext(fmt: str) -> str:
        normalized = (fmt or "webp").lower()
        if normalized in {"jpeg", "jpg"}:
            return "jpg"
        if normalized == "png":
            return "png"
        return "webp"

    @staticmethod
    def _thumbnail_cache_root(storage: Storage) -> Path:
        if (storage.type or "").lower() == "local":
            base = (storage.base_path_or_bucket or "storage").strip() or "storage"
            return (Path(base).resolve() / ".thumb-cache")
        return Path(tempfile.gettempdir()).resolve() / "cowdisk-thumb-cache"

    @classmethod
    def _thumbnail_cache_path(
        cls,
        storage: Storage,
        file_id: int,
        cache_key: str,
        fmt: str,
    ) -> Path:
        root = cls._thumbnail_cache_root(storage)
        ext = cls._thumbnail_ext(fmt)
        shard = cache_key[:2] or "00"
        return root / str(file_id) / shard / f"{cache_key}.{ext}"

    @classmethod
    def _thumbnail_cache_file_dir(cls, storage: Storage, file_id: int) -> Path:
        root = cls._thumbnail_cache_root(storage)
        return root / str(file_id)

    @staticmethod
    async def _read_cached_thumbnail(path: Path) -> bytes | None:
        def _sync_read() -> bytes | None:
            if not path.exists() or not path.is_file():
                return None
            return path.read_bytes()

        return await asyncio.to_thread(_sync_read)

    @staticmethod
    async def _write_cached_thumbnail(path: Path, content: bytes) -> None:
        def _sync_write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = path.with_name(f".{path.name}.tmp-{uuid4().hex}")
            temp_path.write_bytes(content)
            temp_path.replace(path)

        await asyncio.to_thread(_sync_write)

    @classmethod
    async def _purge_thumbnail_cache_for_file(cls, storage: Storage, file_id: int) -> None:
        cache_dir = cls._thumbnail_cache_file_dir(storage, file_id)

        def _sync_delete() -> None:
            if cache_dir.exists():
                import shutil

                shutil.rmtree(cache_dir, ignore_errors=True)

        await asyncio.to_thread(_sync_delete)

    @staticmethod
    def _render_image_thumbnail(
        abs_path: Path,
        width: int,
        height: int,
        fit: str,
        fmt: str,
        quality: int,
    ) -> tuple[bytes, str]:
        with Image.open(abs_path) as image:
            source = image.copy()
        if fit == "contain":
            source.thumbnail((width, height), Image.Resampling.LANCZOS)
            if fmt in {"jpeg", "jpg"}:
                canvas = Image.new("RGB", (width, height), (255, 255, 255))
                offset = ((width - source.width) // 2, (height - source.height) // 2)
                if source.mode not in {"RGB", "L"}:
                    source = source.convert("RGB")
                canvas.paste(source, offset)
                rendered = canvas
            else:
                canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                offset = ((width - source.width) // 2, (height - source.height) // 2)
                if source.mode != "RGBA":
                    source = source.convert("RGBA")
                canvas.paste(source, offset)
                rendered = canvas
        else:
            rendered = ImageOps.fit(
                source,
                (width, height),
                method=Image.Resampling.LANCZOS,
            )
        format_name = "WEBP"
        media_type = "image/webp"
        save_kwargs: dict[str, int | bool] = {"quality": quality}
        normalized_fmt = fmt.lower()
        if normalized_fmt in {"jpeg", "jpg"}:
            format_name = "JPEG"
            media_type = "image/jpeg"
            if rendered.mode not in {"RGB", "L"}:
                rendered = rendered.convert("RGB")
            save_kwargs = {"quality": quality, "optimize": True}
        elif normalized_fmt == "png":
            format_name = "PNG"
            media_type = "image/png"
            save_kwargs = {"optimize": True}
        else:
            if rendered.mode not in {"RGB", "RGBA", "L"}:
                rendered = rendered.convert("RGBA")
            save_kwargs = {"quality": quality, "method": 6}
        buffer = io.BytesIO()
        rendered.save(buffer, format=format_name, **save_kwargs)
        return buffer.getvalue(), media_type

    @classmethod
    async def build_thumbnail(
        cls,
        request: Request,
        db: AsyncSession,
        file_id: int,
        user_id: int,
        width: int = 128,
        height: int = 128,
        fit: str = "cover",
        fmt: str = "webp",
        quality: int = 82,
    ) -> Response:
        entry = await cls._get_active_file(db, user_id, file_id)
        if entry.is_dir:
            raise ThumbnailNotSupported("目录不支持缩略图预览")
        width = cls._normalize_thumbnail_size(width, 128)
        height = cls._normalize_thumbnail_size(height, 128)
        fit_mode = (fit or "cover").strip().lower()
        if fit_mode not in {"cover", "contain"}:
            fit_mode = "cover"
        fmt_mode = (fmt or "webp").strip().lower()
        if fmt_mode not in {"webp", "jpeg", "jpg", "png"}:
            fmt_mode = "webp"
        quality_value = max(30, min(95, int(quality or 82)))
        kind = cls._guess_preview_kind(entry)
        if kind == "pdf":
            raise ThumbnailNotSupported("PDF 缩略图暂未启用")
        if kind == "video":
            raise ThumbnailNotSupported("视频封面预览暂未启用")
        if kind != "image":
            raise ThumbnailNotSupported()
        storage = await cls._get_storage_by_id(db, entry.storage_id)
        backend = get_storage_backend(storage)
        abs_path = backend.resolve_abs_path(entry.storage_path)
        if not backend.exists_abs_path(abs_path):
            raise FileNotFound()
        if entry.updated_at:
            version = int(entry.updated_at.timestamp())
        else:
            version = 0
        etag = sha1(
            f"{entry.id}:{entry.etag or ''}:{width}:{height}:{fit_mode}:{fmt_mode}:{quality_value}:{version}".encode(
                "utf-8"
            )
        ).hexdigest()
        if_none_match = (request.headers.get("if-none-match") or "").strip().strip('"')
        if if_none_match == etag:
            return Response(status_code=304, headers={"ETag": etag})
        cache_path = cls._thumbnail_cache_path(
            storage=storage,
            file_id=entry.id,
            cache_key=etag,
            fmt=fmt_mode,
        )
        cached_blob = await cls._read_cached_thumbnail(cache_path)
        if cached_blob is not None:
            return Response(
                content=cached_blob,
                media_type=cls._thumbnail_media_type(fmt_mode),
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "ETag": etag,
                    "Content-Disposition": content_disposition(
                        f"{PurePosixPath(entry.name).stem}.thumb.{cls._thumbnail_ext(fmt_mode)}",
                        inline=True,
                    ),
                },
            )
        try:
            blob, media_type = await asyncio.to_thread(
                cls._render_image_thumbnail,
                abs_path,
                width,
                height,
                fit_mode,
                fmt_mode,
                quality_value,
            )
        except UnidentifiedImageError as exc:
            raise ThumbnailBuildFailed("无法解析图片内容") from exc
        except OSError as exc:
            raise ThumbnailBuildFailed(f"缩略图生成失败: {exc}") from exc
        try:
            await cls._write_cached_thumbnail(cache_path, blob)
        except Exception:
            # 缓存写入失败不影响主流程，直接返回实时生成结果。
            pass
        return Response(
            content=blob,
            media_type=media_type,
            headers={
                "Cache-Control": "public, max-age=86400",
                "ETag": etag,
                "Content-Disposition": content_disposition(
                    f"{PurePosixPath(entry.name).stem}.thumb.{cls._thumbnail_ext(fmt_mode)}",
                    inline=True,
                ),
            },
        )

    @classmethod
    async def save_text_file(
        cls,
        db: AsyncSession,
        file_id: int,
        content: str,
        user_id: int,
        overwrite: bool = False,
    ) -> File:
        """
        保存文本文件内容。
        仅允许写入未删除文件。
        overwrite 用于控制冲突处理。
        写入由存储后端原子替换完成。
        成功后更新 size/etag/content_hash。
        并发：同文件写入存在覆盖风险。
        性能：整文本写入，适合小文件。
        返回：更新后的 File 记录。
        """
        file = await cls._get_active_file(db, user_id, file_id)
        if file.is_dir:
            raise InvalidTargetType()
        storage = await cls._get_storage_by_id(db, file.storage_id)
        backend = get_storage_backend(storage)
        expected_size = len(content.encode("utf-8"))
        additional = max(0, expected_size - int(file.size or 0))
        await cls._ensure_quota_available(db, user_id, additional)
        size, digest = await backend.write_text(file.storage_path, content)
        file.size = size
        file.etag = digest
        file.content_hash = digest
        await db.commit()
        await db.refresh(file)
        return file

    @classmethod
    async def prepare_download(
        cls, db: AsyncSession, file_id: int, user_id: int
    ) -> tuple[Path, str, bool, int]:
        """
        准备下载目标的实际路径。
        仅支持下载文件，不支持目录。
        返回路径、文件名、是否需要清理以及文件大小。
        允许后端根据存储类型决定是否生成临时文件。
        权限由调用方校验，不在此重复鉴权。
        并发安全：只读操作不修改状态。
        性能：单条查询 + 可能的路径解析。
        返回：下载路径与元信息。
        """
        file = await cls._get_active_file(db, user_id, file_id)
        storage = await cls._get_storage_by_id(db, file.storage_id)
        backend = get_storage_backend(storage)
        if file.is_dir:
            raise BadRequestException("目录下载需使用打包下载接口")
        target = backend.resolve_abs_path(file.storage_path)
        return target, file.name, False, storage.id

    @classmethod
    async def create_download_job(
        cls, db: AsyncSession, file_id: int, user_id: int, redis
    ) -> str:
        file = await cls._get_active_file(db, user_id, file_id)
        if not file.is_dir:
            raise BadRequestException("文件无需打包")
        job_id = uuid4().hex
        key = f"disk:download:{job_id}"
        await redis.hset(
            key,
            mapping={
                "status": "ready",
                "user_id": str(user_id),
                "file_id": str(file_id),
                "filename": f"{file.name or 'root'}.zip",
            },
        )
        await redis.expire(key, 10800)
        return job_id

    @classmethod
    async def create_compress_job(
        cls, db: AsyncSession, file_id: int, user_id: int, name: str | None, redis
    ) -> str:
        """
        创建压缩任务并异步执行。
        任务状态存入 Redis 以支持轮询。
        压缩完成后会生成新的文件条目。
        权限由调用方校验，不在此重复。
        并发：同一文件可多次创建任务。
        失败时会写入 error 字段。
        性能：任务执行由后台线程控制。
        返回：job_id。
        """
        job_id = uuid4().hex
        key = f"disk:compress:{job_id}"
        await redis.hset(
            key,
            mapping={
                "status": "pending",
                "user_id": str(user_id),
                "file_id": str(file_id),
                "name": name or "",
                "usage_updated": "0",
            },
        )
        await redis.expire(key, 10800)
        asyncio.create_task(
            cls._run_compress_job(job_id, user_id, file_id, name, redis)
        )
        return job_id

    @classmethod
    async def create_compress_batch_job(
        cls, db: AsyncSession, file_ids: list[int], user_id: int, name: str | None, redis
    ) -> str:
        ids = [int(file_id) for file_id in file_ids if int(file_id) > 0]
        if not ids:
            raise ZipTargetRequired()
        job_id = uuid4().hex
        key = f"disk:compress:{job_id}"
        await redis.hset(
            key,
            mapping={
                "status": "pending",
                "user_id": str(user_id),
                "file_ids": ",".join(str(i) for i in ids),
                "name": name or "",
                "usage_updated": "0",
            },
        )
        await redis.expire(key, 10800)
        asyncio.create_task(
            cls._run_compress_batch_job(job_id, user_id, ids, name, redis)
        )
        return job_id

    @classmethod
    async def create_extract_job(
        cls, db: AsyncSession, file_id: int, user_id: int, redis
    ) -> str:
        """
        创建解压任务并异步执行。
        任务状态存入 Redis 以支持轮询。
        解压完成后会生成目录条目。
        权限由调用方校验，不在此重复。
        并发：同一文件可多次创建任务。
        失败时会写入 error 字段。
        性能：任务执行由后台线程控制。
        返回：job_id。
        """
        file = await cls._get_active_file(db, user_id, file_id)
        if file.is_dir:
            raise InvalidTargetType()
        if not file.name.lower().endswith(".zip"):
            raise BadRequestException("仅支持 ZIP 文件解压")
        job_id = uuid4().hex
        key = f"disk:extract:{job_id}"
        await redis.hset(
            key,
            mapping={
                "status": "pending",
                "user_id": str(user_id),
                "file_id": str(file_id),
                "usage_updated": "0",
            },
        )
        await redis.expire(key, 10800)
        asyncio.create_task(cls._run_extract_job(job_id, user_id, file_id, redis))
        return job_id

    @classmethod
    async def get_compress_job_status(cls, job_id: str, user_id: int, redis) -> dict:
        """
        获取压缩任务状态。
        仅允许读取当前用户的任务。
        状态包含 pending/ready/error。
        错误信息通过 message 返回。
        幂等：重复查询返回一致结果。
        性能：单次 Redis 读取。
        失败：任务不存在会抛出异常。
        返回：状态字典。
        """
        key = f"disk:compress:{job_id}"
        decoded = await cls._get_job_data(key, user_id, redis, "压缩任务不存在")
        return {
            "status": decoded.get("status", "pending"),
            "message": decoded.get("error", ""),
            "output_path": decoded.get("output_path", ""),
            "usage_updated": decoded.get("usage_updated", "0"),
        }

    @classmethod
    async def get_extract_job_status(cls, job_id: str, user_id: int, redis) -> dict:
        """
        获取解压任务状态。
        仅允许读取当前用户的任务。
        状态包含 pending/ready/error。
        错误信息通过 message 返回。
        幂等：重复查询返回一致结果。
        性能：单次 Redis 读取。
        失败：任务不存在会抛出异常。
        返回：状态字典。
        """
        key = f"disk:extract:{job_id}"
        decoded = await cls._get_job_data(key, user_id, redis, "解压任务不存在")
        return {
            "status": decoded.get("status", "pending"),
            "message": decoded.get("error", ""),
            "output_path": decoded.get("output_path", ""),
            "usage_updated": decoded.get("usage_updated", "0"),
        }

    @classmethod
    async def get_download_job_status(cls, job_id: str, user_id: int, redis) -> dict:
        key = f"disk:download:{job_id}"
        decoded = await cls._get_job_data(key, user_id, redis, "下载任务不存在")
        return {
            "status": decoded.get("status", "pending"),
            "message": decoded.get("error", ""),
            "filename": decoded.get("filename", ""),
        }

    @classmethod
    async def get_download_job_target(
        cls, db: AsyncSession, job_id: str, user_id: int, redis
    ) -> tuple[File, str]:
        key = f"disk:download:{job_id}"
        decoded = await cls._get_job_data(key, user_id, redis, "下载任务不存在")
        if decoded.get("status") != "ready":
            raise TaskNotReady()
        file_id = int(decoded.get("file_id", "0"))
        if file_id <= 0:
            raise TaskInvalid("任务数据缺失")
        root = await cls._get_active_file(db, user_id, file_id)
        if not root.is_dir:
            raise BadRequestException("目标不是目录")
        filename = decoded.get("filename", f"{root.name or 'root'}.zip")
        return root, filename

    @classmethod
    async def _get_job_data(
        cls, key: str, user_id: int, redis, not_found_msg: str
    ) -> dict:
        data = await redis.hgetall(key)
        if not data:
            raise TaskInvalid(not_found_msg)
        decoded = cls._decode_redis_hash(data)
        if decoded.get("user_id") != str(user_id):
            raise NoPermission("无权访问该任务")
        return decoded

    @classmethod
    async def _run_compress_job(
        cls,
        job_id: str,
        user_id: int,
        file_id: int,
        name: str | None,
        redis,
    ) -> None:
        key = f"disk:compress:{job_id}"
        try:
            async with async_session() as session:
                entry = await cls.compress_by_id(session, user_id, file_id, name)
            await cls._set_job_ready(
                key,
                redis,
                {
                    "status": "ready",
                    "output_path": rel_path_from_storage(
                        entry.user_id, entry.storage_path
                    ),
                    "usage_updated": "0",
                },
            )
        except Exception as exc:
            await cls._set_job_error(key, redis, exc)

    @classmethod
    async def _run_compress_batch_job(
        cls,
        job_id: str,
        user_id: int,
        file_ids: list[int],
        name: str | None,
        redis,
    ) -> None:
        key = f"disk:compress:{job_id}"
        try:
            async with async_session() as session:
                entry = await cls.compress_many_by_ids(session, user_id, file_ids, name)
            await cls._set_job_ready(
                key,
                redis,
                {
                    "status": "ready",
                    "output_path": rel_path_from_storage(
                        entry.user_id, entry.storage_path
                    ),
                    "usage_updated": "0",
                },
            )
        except Exception as exc:
            await cls._set_job_error(key, redis, exc)

    @classmethod
    async def _run_extract_job(
        cls, job_id: str, user_id: int, file_id: int, redis
    ) -> None:
        key = f"disk:extract:{job_id}"
        try:
            async with async_session() as session:
                entry = await cls.extract_by_id(session, user_id, file_id)
            await cls._set_job_ready(
                key,
                redis,
                {
                    "status": "ready",
                    "output_path": rel_path_from_storage(
                        entry.user_id, entry.storage_path
                    ),
                    "usage_updated": "0",
                },
            )
        except Exception as exc:
            await cls._set_job_error(key, redis, exc)

    @staticmethod
    async def _set_job_ready(key: str, redis, mapping: dict, ttl: int = 10800) -> None:
        await redis.hset(key, mapping=mapping)
        await redis.expire(key, ttl)

    @staticmethod
    async def _set_job_error(key: str, redis, exc: Exception, ttl: int = 600) -> None:
        await redis.hset(key, mapping={"status": "error", "error": str(exc)})
        await redis.expire(key, ttl)

    @classmethod
    async def stream_zip_dir(
        cls, request: Request, db: AsyncSession, root: File, filename: str
    ) -> StreamingResponse:
        """
        流式打包目录并输出 ZIP。
        仅依赖 DB 列表，不进行磁盘遍历。
        通过 zipstream 按块输出避免高内存占用。
        客户端断开连接后立即停止打包。
        目录项以逻辑相对路径写入 ZIP。
        并发：读取文件时不持有全局锁。
        性能：读取大文件时 I/O 持续占用。
        返回：StreamingResponse。
        """
        storage = await cls._get_storage_by_id(db, root.storage_id)
        backend = get_storage_backend(storage)
        descendants = await cls._collect_descendant_entries(db, root.user_id, [root.id])
        root_prefix = root.storage_path.rstrip("/")
        zip_root = root.name or "root"
        total_files = len(descendants)
        logger.info("开始流式打包下载: %s, items=%s", filename, total_files)

        def _rel_path(item: File) -> str:
            if item.storage_path.startswith(root_prefix + "/"):
                return item.storage_path[len(root_prefix) + 1 :]
            return item.name

        cancel_flag = {"stop": False}

        class _FileIter:
            def __init__(self, file_path: Path, should_stop):
                self._file = file_path.open("rb")
                self._stop = should_stop

            def __iter__(self):
                return self

            def __next__(self):
                if self._stop():
                    self._file.close()
                    raise StopIteration
                data = self._file.read(1024 * 1024)
                if not data:
                    self._file.close()
                    raise StopIteration
                return data

        def _should_stop() -> bool:
            return cancel_flag["stop"]

        # sized=True 需要 ZIP_STORED，保证流式写入稳定。
        zf = zipstream.ZipStream(compress_type=zipstream.ZIP_STORED, sized=True)
        zf.add(b"", f"{zip_root}/")
        for item in descendants:
            rel = _rel_path(item)
            arcname = f"{zip_root}/{rel}" if rel else zip_root
            if item.is_dir:
                zf.add(b"", arcname.rstrip("/") + "/")
                continue
            abs_path = backend.resolve_abs_path(item.storage_path)
            try:
                size = abs_path.stat().st_size
            except OSError:
                continue
            zf.add(_FileIter(abs_path, _should_stop), arcname, size=size)

        async def _stream():
            try:
                for chunk in zf:
                    if await request.is_disconnected():
                        cancel_flag["stop"] = True
                        logger.info("客户端下载中断: %s", filename)
                        break
                    yield chunk
            finally:
                # 断开时及时停止文件迭代，减少 I/O 浪费。
                cancel_flag["stop"] = True

        headers = {"Content-Disposition": content_disposition(filename, inline=False)}
        return StreamingResponse(
            _stream(), media_type="application/zip", headers=headers
        )

    @classmethod
    async def _zip_dir_by_db(cls, db: AsyncSession, root: File, user_id: int) -> Path:
        storage = await cls._get_storage_by_id(db, root.storage_id)
        backend = get_storage_backend(storage)
        descendants = await cls._collect_descendant_entries(db, user_id, [root.id])
        root_prefix = root.storage_path.rstrip("/")

        def _rel_path(item: File) -> str:
            if item.storage_path.startswith(root_prefix + "/"):
                return item.storage_path[len(root_prefix) + 1 :]
            return item.name

        entries = [
            (item.storage_path, _rel_path(item), item.is_dir) for item in descendants
        ]
        return await backend.create_zip(user_id, root.name or "root", entries)

    @classmethod
    async def compress_by_id(
        cls, db: AsyncSession, user_id: int, file_id: int, name: str | None
    ) -> File:
        target = await cls._get_active_file(db, user_id, file_id)
        parent_id = target.parent_id
        parent = None
        if parent_id is not None:
            parent = await cls._get_active_dir(db, user_id, parent_id)
        base_name = name or (target.name or "archive")
        safe_name = cls._ensure_zip_extension(base_name)
        safe_name = await cls._generate_unique_name_with_suffix(
            db,
            user_id,
            parent_id,
            safe_name,
            suffix=" (压缩)",
            conflict_error=ZipTooManyConflicts(),
        )
        storage = await cls._get_storage_by_id(db, target.storage_id)
        backend = get_storage_backend(storage)
        storage_path = cls._storage_path_for(user_id, parent, safe_name)
        if target.is_dir:
            zip_path = await cls._zip_dir_by_db(db, target, user_id)
            await backend.move_abs_path(zip_path, storage_path)
        else:
            entries = [(target.storage_path, target.name or "file", False)]
            zip_path = await backend.create_zip(user_id, None, entries)
            await backend.move_abs_path(zip_path, storage_path)
        try:
            size, digest = await backend.hash_file(storage_path)
            await cls._ensure_quota_available(db, user_id, size)
        except Exception:
            try:
                await backend.delete(storage_path, is_dir=False)
            except Exception:
                pass
            raise
        entry = File(
            user_id=user_id,
            parent_id=parent_id,
            name=safe_name,
            is_dir=False,
            size=size,
            mime_type="application/zip",
            etag=digest,
            storage_id=storage.id,
            storage_path=storage_path,
            storage_path_hash=cls._hash_storage_path(storage_path),
            content_hash=digest,
            is_deleted=False,
            deleted_at=None,
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry

    @classmethod
    async def compress_many_by_ids(
        cls, db: AsyncSession, user_id: int, file_ids: list[int], name: str | None
    ) -> File:
        unique_ids = cls._dedupe_keep_order(file_ids)
        if not unique_ids:
            raise ZipTargetRequired()

        targets = [await cls._get_active_file(db, user_id, file_id) for file_id in unique_ids]
        first_parent_id = targets[0].parent_id
        for target in targets:
            if target.parent_id != first_parent_id:
                raise BadRequestException("批量压缩仅支持同一目录下的文件")

        parent = None
        if first_parent_id is not None:
            parent = await cls._get_active_dir(db, user_id, first_parent_id)

        base_name = name or "archive.zip"
        safe_name = cls._ensure_zip_extension(base_name)
        safe_name = await cls._generate_unique_name_with_suffix(
            db,
            user_id,
            first_parent_id,
            safe_name,
            suffix=" (压缩)",
            conflict_error=ZipTooManyConflicts(),
        )

        storage = await cls._get_storage_by_id(db, targets[0].storage_id)
        for target in targets:
            if target.storage_id != storage.id:
                raise BadRequestException("批量压缩仅支持同一存储内的文件")
        backend = get_storage_backend(storage)

        def _unique_arc(base: str, used: set[str]) -> str:
            if base not in used:
                used.add(base)
                return base
            dot = base.rfind(".")
            has_ext = dot > 0 and dot < len(base) - 1
            stem = base[:dot] if has_ext else base
            ext = base[dot:] if has_ext else ""
            for i in range(1, 1000):
                candidate = f"{stem} ({i}){ext}"
                if candidate not in used:
                    used.add(candidate)
                    return candidate
            raise ZipTooManyConflicts()

        entries: list[tuple[str, str, bool]] = []
        used_arcnames: set[str] = set()
        for target in targets:
            root_arc = _unique_arc(target.name or str(target.id), used_arcnames)
            if target.is_dir:
                entries.append((target.storage_path, root_arc, True))
                descendants = await cls._collect_descendant_entries(db, user_id, [target.id])
                root_prefix = target.storage_path.rstrip("/")
                for child in descendants:
                    if child.storage_path.startswith(root_prefix + "/"):
                        rel = child.storage_path[len(root_prefix) + 1 :]
                    else:
                        rel = child.name
                    arc = f"{root_arc}/{rel}" if rel else root_arc
                    entries.append((child.storage_path, arc, child.is_dir))
            else:
                entries.append((target.storage_path, root_arc, False))

        zip_path = await backend.create_zip(user_id, None, entries)
        storage_path = cls._storage_path_for(user_id, parent, safe_name)
        await backend.move_abs_path(zip_path, storage_path)
        try:
            size, digest = await backend.hash_file(storage_path)
            await cls._ensure_quota_available(db, user_id, size)
        except Exception:
            try:
                await backend.delete(storage_path, is_dir=False)
            except Exception:
                pass
            raise
        entry = File(
            user_id=user_id,
            parent_id=first_parent_id,
            name=safe_name,
            is_dir=False,
            size=size,
            mime_type="application/zip",
            etag=digest,
            storage_id=storage.id,
            storage_path=storage_path,
            storage_path_hash=cls._hash_storage_path(storage_path),
            content_hash=digest,
            is_deleted=False,
            deleted_at=None,
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry

    @classmethod
    async def extract_by_id(cls, db: AsyncSession, user_id: int, file_id: int) -> File:
        source = await cls._get_active_file(db, user_id, file_id)
        if source.is_dir:
            raise InvalidTargetType()
        if not source.name.lower().endswith(".zip"):
            raise BadRequestException("仅支持 ZIP 文件解压")
        base_name = ensure_name(source.name.rsplit(".", 1)[0] or "extract")
        root_name = await cls._generate_unique_name_with_suffix(
            db,
            user_id,
            source.parent_id,
            base_name,
            suffix=" (解压)",
            conflict_error=ZipTooManyConflicts("解压失败：重名过多"),
        )
        root_dir = await cls.create_dir(db, user_id, source.parent_id, root_name)
        storage = await cls._get_storage_by_id(db, source.storage_id)
        backend = get_storage_backend(storage)
        try:
            extracted = await backend.extract_zip(
                source.storage_path, root_dir.storage_path
            )
            extract_total = sum(int(item.size or 0) for item in extracted if not item.is_dir)
            await cls._ensure_quota_available(db, user_id, extract_total)

            dir_map: dict[str, File] = {"": root_dir}
            dir_paths: set[str] = set()
            for item in extracted:
                rel = PurePosixPath(item.rel_path)
                if item.is_dir:
                    if rel.as_posix():
                        dir_paths.add(rel.as_posix())
                    continue
                for parent in rel.parents:
                    key = parent.as_posix()
                    if key in ("", "."):
                        break
                    dir_paths.add(key)

            for dir_path in sorted(dir_paths, key=lambda p: len(PurePosixPath(p).parts)):
                rel = PurePosixPath(dir_path)
                parent_key = rel.parent.as_posix()
                if parent_key in (".", ""):
                    parent_key = ""
                parent_entry = dir_map.get(parent_key, root_dir)
                storage_path = cls._storage_path_for(user_id, parent_entry, rel.name)
                entry = File(
                    user_id=user_id,
                    parent_id=parent_entry.id,
                    name=rel.name,
                    is_dir=True,
                    size=0,
                    mime_type=None,
                    etag=uuid4().hex,
                    storage_id=storage.id,
                    storage_path=storage_path,
                    storage_path_hash=cls._hash_storage_path(storage_path),
                    content_hash=None,
                    is_deleted=False,
                    deleted_at=None,
                )
                db.add(entry)
                await db.flush()
                dir_map[rel.as_posix()] = entry

            for item in extracted:
                if item.is_dir:
                    continue
                rel = PurePosixPath(item.rel_path)
                parent_key = rel.parent.as_posix()
                if parent_key in (".", ""):
                    parent_key = ""
                parent_entry = dir_map.get(parent_key, root_dir)
                storage_path = cls._storage_path_for(user_id, parent_entry, rel.name)
                digest = item.content_hash or uuid4().hex
                entry = File(
                    user_id=user_id,
                    parent_id=parent_entry.id,
                    name=rel.name,
                    is_dir=False,
                    size=item.size,
                    mime_type=item.mime_type or mimetypes.guess_type(rel.name)[0],
                    etag=digest,
                    storage_id=storage.id,
                    storage_path=storage_path,
                    storage_path_hash=cls._hash_storage_path(storage_path),
                    content_hash=item.content_hash,
                    is_deleted=False,
                    deleted_at=None,
                )
                db.add(entry)
            await db.commit()
            await db.refresh(root_dir)
            return root_dir
        except Exception:
            await db.rollback()
            try:
                await cls._hard_delete_ids(db, user_id, [root_dir.id])
            except Exception:
                pass
            raise

    @classmethod
    async def list_trash(cls, user_id: int, db: AsyncSession) -> dict:
        """
        获取回收站列表，仅返回顶层已删除项。
        顶层判定基于 parent_id 是否仍在删除集合内。
        逻辑路径通过父链回溯得到，避免依赖存储路径。
        仅查询 DB，不扫描磁盘。
        幂等：同一删除状态返回一致结果。
        性能：一次查询 + 若干父链查询。
        返回：回收站条目列表结构。
        错误：数据库异常将向上抛出。
        """
        stmt = (
            select(File)
            .where(
                File.user_id == user_id,
                File.is_deleted == True,
            )
            .order_by(File.deleted_at.desc())
        )
        rows = (await db.exec(stmt)).all()
        if not rows:
            return {"items": []}
        deleted_ids = {row.id for row in rows}

        top_level_rows = [
            row for row in rows if row.parent_id is None or row.parent_id not in deleted_ids
        ]

        async def _logical_path(row: File) -> str:
            parts = [row.name]
            seen = {row.id}
            current_id = row.parent_id
            while current_id is not None:
                if current_id in seen:
                    break
                seen.add(current_id)
                parent = (
                    await db.exec(
                        select(File).where(
                            File.id == current_id,
                            File.user_id == user_id,
                        )
                    )
                ).first()
                if not parent:
                    break
                parts.append(parent.name)
                current_id = parent.parent_id
            return "/".join(reversed(parts))

        items = [
            {
                "id": str(row.id),
                "name": row.name,
                "path": await _logical_path(row),
                "is_dir": row.is_dir,
                "size": row.size,
                "deleted_at": row.deleted_at or datetime.now(),
            }
            for row in top_level_rows
        ]
        return {"items": items}

    @classmethod
    async def restore_trash(cls, file_id: int, user_id: int, db: AsyncSession) -> File:
        """
        回收站恢复快捷入口。
        内部复用 restore 逻辑保持一致。
        仅允许恢复当前用户的条目。
        失败时抛出 ServiceException。
        并发：依赖唯一约束检测冲突。
        性能：目录恢复成本与子孙数相关。
        返回：恢复后的条目。
        """
        return await cls.restore(db, user_id, file_id)

    @classmethod
    async def batch_restore_trash(
        cls, ids: list[int], user_id: int, db: AsyncSession
    ) -> dict:
        if not ids:
            return {"success": 0, "failed": []}
        success = 0
        failed: list[str] = []
        for file_id in ids:
            try:
                await cls.restore(db, user_id, file_id)
                success += 1
            except Exception:
                failed.append(str(file_id))
        return {"success": success, "failed": failed}

    @classmethod
    async def delete_trash(cls, file_id: int, user_id: int, db: AsyncSession) -> bool:
        """
        彻底删除单个回收站条目。
        物理删除将移除真实文件与 DB 记录。
        目录会级联删除全部子孙节点。
        幂等：重复删除已不存在条目会抛错。
        并发：删除过程中不建议并行恢复。
        性能：取决于目录大小。
        返回：True 表示成功。
        """
        await cls._hard_delete_ids(db, user_id, [file_id])
        return True

    @classmethod
    async def batch_delete_trash(
        cls, ids: list[int], user_id: int, db: AsyncSession
    ) -> dict:
        if not ids:
            return {"success": 0, "failed": []}
        success = 0
        failed: list[str] = []
        for file_id in ids:
            try:
                await cls._hard_delete_ids(db, user_id, [file_id])
                success += 1
            except Exception:
                failed.append(str(file_id))
        return {"success": success, "failed": failed}

    @classmethod
    async def clear_trash(cls, user_id: int, db: AsyncSession) -> int:
        """
        清空当前用户回收站。
        会遍历所有已删除记录并物理删除。
        目录会级联删除子孙节点。
        幂等：回收站为空时返回 0。
        并发：清理期间不建议并行恢复。
        性能：回收站大小决定耗时。
        返回：清理数量。
        """
        stmt = select(File.id).where(
            File.user_id == user_id,
            File.is_deleted == True,
        )
        ids = (await db.exec(stmt)).all()
        if not ids:
            return 0
        await cls._hard_delete_ids(db, user_id, ids)
        return len(ids)

    @classmethod
    async def _hard_delete_ids(
        cls, db: AsyncSession, user_id: int, ids: list[int]
    ) -> None:
        if not ids:
            return
        stmt = select(File).where(
            File.user_id == user_id,
            File.id.in_(ids),
        )
        roots = (await db.exec(stmt)).all()
        all_ids: set[int] = set()
        for root in roots:
            all_ids.add(root.id)
            if root.is_dir:
                all_ids.update(
                    await cls._collect_descendants(
                        db, user_id, [root.id], include_deleted=True
                    )
                )
        files = (await db.exec(select(File).where(File.id.in_(all_ids)))).all()
        for item in sorted(files, key=lambda f: len(f.storage_path), reverse=True):
            storage = await cls._get_storage_by_id(db, item.storage_id)
            backend = get_storage_backend(storage)
            try:
                await backend.delete(item.storage_path, item.is_dir)
                # 清理回收站空目录，避免残留时间戳目录。
                if item.storage_path.startswith(".trash/") and hasattr(
                    backend, "cleanup_empty_parents"
                ):
                    try:
                        trash_root = f".trash/{user_id}"
                        backend.cleanup_empty_parents(item.storage_path, trash_root)
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                await cls._purge_thumbnail_cache_for_file(storage, item.id)
            except Exception:
                pass
        await db.execute(File.__table__.delete().where(File.id.in_(all_ids)))
        await db.commit()



