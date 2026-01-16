"""
@File: disk.py
@Author: GuaiMiu
@Date: 2025/4/5 20:26
@Version: 1.0
@Description:
"""

import asyncio
import json
import shutil
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from pathlib import PurePosixPath
from uuid import uuid4

from fastapi import UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession

from app.admin.dao.user import user_crud
from app.core.config import settings
from app.core.exception import ServiceException
from app.disk.schemas.disk import (
    DiskDeleteIn,
    DiskDeleteOut,
    DiskEntry,
    DiskListOut,
    DiskRenameIn,
    DiskUploadOut,
    DiskTrashEntry,
    DiskTrashListOut,
    DiskShareEntry,
    DiskShareListOut,
)


class DiskService:
    """
    网盘服务类
    """

    _root: Path | None = None

    @classmethod
    def _get_root(cls) -> Path:
        if cls._root is None:
            root = Path(settings.DISK_ROOT or "storage").resolve()
            root.mkdir(parents=True, exist_ok=True)
            cls._root = root
        return cls._root

    @classmethod
    def _get_user_root(cls, user_id: int) -> Path:
        root = cls._get_root() / str(user_id)
        root.mkdir(parents=True, exist_ok=True)
        return root

    @classmethod
    def _resolve_path(cls, relative_path: str, user_id: int) -> Path:
        root = cls._get_user_root(user_id)
        rel = Path(relative_path or "")
        if rel.is_absolute() or rel.drive:
            raise ServiceException(msg="非法路径")
        resolved = (root / rel).resolve()
        if not resolved.is_relative_to(root):
            raise ServiceException(msg="非法路径")
        return resolved

    @classmethod
    def _relative_path(cls, path: Path, user_id: int) -> str:
        root = cls._get_user_root(user_id)
        if path == root:
            return ""
        return path.relative_to(root).as_posix()

    @classmethod
    def _get_tmp_dir(cls, user_id: int) -> Path:
        tmp_dir = cls._get_root() / ".tmp" / str(user_id)
        tmp_dir.mkdir(parents=True, exist_ok=True)
        return tmp_dir

    @classmethod
    def _get_trash_dir(cls, user_id: int) -> Path:
        trash_dir = cls._get_root() / ".trash" / str(user_id)
        trash_dir.mkdir(parents=True, exist_ok=True)
        return trash_dir

    @classmethod
    def _get_trash_index(cls, user_id: int) -> Path:
        return cls._get_trash_dir(user_id) / "index.json"

    @classmethod
    def _get_share_root(cls) -> Path:
        root = cls._get_root() / ".share"
        root.mkdir(parents=True, exist_ok=True)
        return root

    @classmethod
    def _get_share_dir(cls, user_id: int) -> Path:
        share_dir = cls._get_share_root() / str(user_id)
        share_dir.mkdir(parents=True, exist_ok=True)
        return share_dir

    @classmethod
    def _get_share_index(cls) -> Path:
        return cls._get_share_root() / "index.json"

    @staticmethod
    def _load_json(path: Path, default):
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return default

    @staticmethod
    def _save_json(path: Path, data) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        temp.replace(path)

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime:
        if not value:
            return datetime.utcnow()
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.utcnow()

    @classmethod
    def _unique_restore_path(cls, desired: Path) -> Path:
        if not desired.exists():
            return desired
        stem = desired.stem
        suffix = desired.suffix
        base = desired.parent
        for idx in range(1, 1000):
            candidate = base / f"{stem} (restored{'' if idx == 1 else f' {idx}'}){suffix}"
            if not candidate.exists():
                return candidate
        raise ServiceException(msg="无法恢复，目标路径冲突")

    @classmethod
    def _to_entry(cls, path: Path, user_id: int) -> DiskEntry:
        stat = path.stat()
        return DiskEntry(
            name=path.name,
            path=cls._relative_path(path, user_id),
            is_dir=path.is_dir(),
            size=0 if path.is_dir() else stat.st_size,
            modified_time=datetime.fromtimestamp(stat.st_mtime),
        )

    @classmethod
    async def list_dir(cls, path: str, user_id: int) -> DiskListOut:
        target = cls._resolve_path(path, user_id)
        if not target.exists():
            raise ServiceException(msg="目录不存在")
        if not target.is_dir():
            raise ServiceException(msg="目标不是目录")
        items = [cls._to_entry(child, user_id) for child in target.iterdir()]
        items.sort(key=lambda entry: (not entry.is_dir, entry.name.lower()))
        return DiskListOut(
            path=cls._relative_path(target, user_id),
            items=items,
        )

    @classmethod
    async def mkdir(cls, path: str, user_id: int) -> DiskEntry:
        target = cls._resolve_path(path, user_id)
        target.mkdir(parents=True, exist_ok=True)
        return cls._to_entry(target, user_id)

    @classmethod
    async def upload(
        cls,
        files: list[UploadFile],
        path: str,
        overwrite: bool,
        user_id: int,
        db: AsyncSession | None = None,
    ) -> DiskUploadOut:
        items: list[DiskEntry] = []
        for upload in files:
            if not upload.filename:
                continue
            target_dir, safe_name = cls._normalize_upload_target(
                path, upload.filename, user_id
            )
            target_file = target_dir / safe_name
            if target_file.exists() and not overwrite:
                raise ServiceException(msg=f"文件已存在: {safe_name}")
            target_dir.mkdir(parents=True, exist_ok=True)
            try:
                with target_file.open("wb") as handle:
                    shutil.copyfileobj(upload.file, handle)
            finally:
                await upload.close()
            items.append(cls._to_entry(target_file, user_id))
        return DiskUploadOut(items=items)

    @classmethod
    def _normalize_upload_target(
        cls, path: str, filename: str, user_id: int
    ) -> tuple[Path, str]:
        base_dir = cls._resolve_path(path, user_id)
        base_dir.mkdir(parents=True, exist_ok=True)
        if not base_dir.is_dir():
            raise ServiceException(msg="目标不是目录")
        if not filename:
            raise ServiceException(msg="文件名不能为空")
        normalized = filename.replace("\\", "/").lstrip("/")
        rel = PurePosixPath(normalized)
        if rel.is_absolute() or ".." in rel.parts:
            raise ServiceException(msg="非法文件名")
        safe_name = rel.name
        if not safe_name:
            raise ServiceException(msg="文件名不能为空")
        rel_dir = Path(*rel.parts[:-1]) if len(rel.parts) > 1 else Path()
        target_dir = (base_dir / rel_dir).resolve()
        user_root = cls._get_user_root(user_id)
        if not target_dir.is_relative_to(user_root):
            raise ServiceException(msg="非法路径")
        return target_dir, safe_name

    @classmethod
    async def init_chunk_upload(
        cls,
        path: str,
        filename: str,
        size: int,
        total_chunks: int,
        overwrite: bool,
        user_id: int,
        redis,
        db: AsyncSession | None = None,
    ) -> str:
        if total_chunks <= 0:
            raise ServiceException(msg="分片数量不合法")
        target_dir, safe_name = cls._normalize_upload_target(path, filename, user_id)
        target_file = target_dir / safe_name
        if target_file.exists() and not overwrite:
            raise ServiceException(msg=f"文件已存在: {safe_name}")
        upload_id = uuid4().hex
        key = f"disk:upload:{upload_id}"
        await redis.hset(
            key,
            mapping={
                "user_id": str(user_id),
                "path": cls._relative_path(target_dir, user_id),
                "filename": safe_name,
                "size": str(size),
                "total_chunks": str(total_chunks),
                "overwrite": "1" if overwrite else "0",
            },
        )
        await redis.expire(key, 10800)
        return upload_id

    @classmethod
    async def upload_chunk(
        cls,
        upload_id: str,
        index: int,
        chunk: UploadFile,
        user_id: int,
        redis,
    ) -> None:
        key = f"disk:upload:{upload_id}"
        data = await redis.hgetall(key)
        if not data:
            raise ServiceException(msg="上传任务不存在")
        info = cls._decode_redis_hash(data)
        if info.get("user_id") != str(user_id):
            raise ServiceException(msg="无权访问该任务")
        total_chunks = int(info.get("total_chunks", "0"))
        if index < 0 or index >= total_chunks:
            raise ServiceException(msg="分片索引不合法")
        tmp_dir = cls._get_tmp_dir(user_id) / upload_id
        tmp_dir.mkdir(parents=True, exist_ok=True)
        chunk_path = tmp_dir / f"{index}.part"
        try:
            with chunk_path.open("wb") as handle:
                shutil.copyfileobj(chunk.file, handle)
        finally:
            await chunk.close()
        await redis.expire(key, 10800)

    @classmethod
    async def complete_chunk_upload(
        cls, upload_id: str, user_id: int, redis
    ) -> DiskEntry:
        key = f"disk:upload:{upload_id}"
        data = await redis.hgetall(key)
        if not data:
            raise ServiceException(msg="上传任务不存在")
        info = cls._decode_redis_hash(data)
        if info.get("user_id") != str(user_id):
            raise ServiceException(msg="无权访问该任务")
        total_chunks = int(info.get("total_chunks", "0"))
        filename = info.get("filename", "")
        if not filename:
            raise ServiceException(msg="文件名缺失")
        target_dir = cls._resolve_path(info.get("path", ""), user_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / filename
        overwrite = info.get("overwrite") == "1"
        if target_file.exists() and not overwrite:
            raise ServiceException(msg=f"文件已存在: {filename}")
        tmp_dir = cls._get_tmp_dir(user_id) / upload_id
        if not tmp_dir.exists():
            raise ServiceException(msg="分片目录不存在")
        for idx in range(total_chunks):
            if not (tmp_dir / f"{idx}.part").exists():
                raise ServiceException(msg="分片未上传完成")
        if target_file.exists() and overwrite:
            target_file.unlink(missing_ok=True)
        with target_file.open("wb") as handle:
            for idx in range(total_chunks):
                chunk_path = tmp_dir / f"{idx}.part"
                with chunk_path.open("rb") as part:
                    shutil.copyfileobj(part, handle)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        await redis.delete(key)
        return cls._to_entry(target_file, user_id)

    @classmethod
    async def get_file_path(cls, path: str, user_id: int) -> Path:
        target = cls._resolve_path(path, user_id)
        if not target.exists():
            raise ServiceException(msg="文件不存在")
        if not target.is_file():
            raise ServiceException(msg="目标不是文件")
        return target

    @classmethod
    async def prepare_download(cls, path: str, user_id: int) -> tuple[Path, str, bool]:
        target = cls._resolve_path(path, user_id)
        if not target.exists():
            raise ServiceException(msg="文件或目录不存在")
        if target.is_file():
            return target, target.name, False
        zip_path = await cls._zip_dir(target, user_id)
        zip_name = f"{(target.name or 'root')}.zip"
        return zip_path, zip_name, True

    @classmethod
    async def _zip_dir(cls, target: Path, user_id: int) -> Path:
        return await asyncio.to_thread(cls._zip_dir_sync, target, user_id)

    @classmethod
    def _zip_dir_sync(cls, target: Path, user_id: int) -> Path:
        tmp_dir = cls._get_tmp_dir(user_id)
        zip_path = tmp_dir / f"{(target.name or 'root')}-{uuid4().hex}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for item in target.rglob("*"):
                if tmp_dir in item.parents:
                    continue
                if item.is_file():
                    arcname = item.relative_to(target).as_posix()
                    zf.write(item, arcname)
                elif item.is_dir():
                    if not any(item.iterdir()):
                        arcname = item.relative_to(target).as_posix().rstrip("/") + "/"
                        zf.writestr(arcname, "")
        return zip_path

    @classmethod
    async def compute_used_space(cls, user_id: int) -> int:
        root = cls._get_user_root(user_id)

        def walk() -> int:
            total = 0
            if not root.exists():
                return total
            for item in root.rglob("*"):
                if item.is_file():
                    try:
                        total += item.stat().st_size
                    except OSError:
                        continue
            return total

        return await asyncio.to_thread(walk)

    @classmethod
    async def refresh_used_space(cls, user_id: int, db: AsyncSession) -> int:
        total = await cls.compute_used_space(user_id)
        user = await user_crud.get_by_id(db, user_id)
        if user:
            user.used_space = total
            await db.commit()
            await db.refresh(user)
        return total


    @classmethod
    async def delete(cls, data: DiskDeleteIn, user_id: int) -> DiskDeleteOut:
        await cls.move_to_trash(data, user_id)
        return DiskDeleteOut(path=data.path, deleted=True)

    @classmethod
    async def move_to_trash(cls, data: DiskDeleteIn, user_id: int) -> DiskTrashEntry:
        target = cls._resolve_path(data.path, user_id)
        if target == cls._get_user_root(user_id):
            raise ServiceException(msg="不允许删除根目录")
        if not target.exists():
            raise ServiceException(msg="文件或目录不存在")
        is_dir = target.is_dir()
        size = 0 if is_dir else target.stat().st_size
        if is_dir and any(target.iterdir()) and not data.recursive:
            raise ServiceException(msg="目录非空，需递归删除")
        trash_dir = cls._get_trash_dir(user_id)
        trash_id = uuid4().hex
        trash_path = trash_dir / trash_id
        shutil.move(str(target), trash_path)
        entry = DiskTrashEntry(
            id=trash_id,
            name=target.name,
            path=cls._relative_path(target, user_id),
            is_dir=is_dir,
            size=size,
            deleted_at=datetime.utcnow(),
        )
        index_path = cls._get_trash_index(user_id)
        items = cls._load_json(index_path, [])
        items.append(
            {
                "id": entry.id,
                "name": entry.name,
                "path": entry.path,
                "is_dir": entry.is_dir,
                "size": entry.size,
                "deleted_at": entry.deleted_at.isoformat(),
            }
        )
        cls._save_json(index_path, items)
        return entry

    @classmethod
    async def list_trash(cls, user_id: int) -> DiskTrashListOut:
        index_path = cls._get_trash_index(user_id)
        items = cls._load_json(index_path, [])
        trash_dir = cls._get_trash_dir(user_id)
        entries: list[DiskTrashEntry] = []
        valid_items = []
        for item in items:
            trash_id = item.get("id")
            if not trash_id:
                continue
            if not (trash_dir / trash_id).exists():
                continue
            entry = DiskTrashEntry(
                id=trash_id,
                name=item.get("name", ""),
                path=item.get("path", ""),
                is_dir=bool(item.get("is_dir", False)),
                size=int(item.get("size", 0)),
                deleted_at=cls._parse_datetime(item.get("deleted_at")),
            )
            entries.append(entry)
            valid_items.append(item)
        if len(valid_items) != len(items):
            cls._save_json(index_path, valid_items)
        return DiskTrashListOut(items=entries)

    @classmethod
    async def restore_trash(cls, trash_id: str, user_id: int) -> DiskEntry:
        index_path = cls._get_trash_index(user_id)
        items = cls._load_json(index_path, [])
        target_item = None
        for item in items:
            if item.get("id") == trash_id:
                target_item = item
                break
        if not target_item:
            raise ServiceException(msg="回收站条目不存在")
        trash_dir = cls._get_trash_dir(user_id)
        trash_path = trash_dir / trash_id
        if not trash_path.exists():
            items = [item for item in items if item.get("id") != trash_id]
            cls._save_json(index_path, items)
            raise ServiceException(msg="回收站条目已丢失")
        desired = cls._resolve_path(target_item.get("path", ""), user_id)
        dest = cls._unique_restore_path(desired)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(trash_path), dest)
        items = [item for item in items if item.get("id") != trash_id]
        cls._save_json(index_path, items)
        return cls._to_entry(dest, user_id)

    @classmethod
    async def delete_trash(cls, trash_id: str, user_id: int) -> bool:
        index_path = cls._get_trash_index(user_id)
        items = cls._load_json(index_path, [])
        target_item = None
        for item in items:
            if item.get("id") == trash_id:
                target_item = item
                break
        if not target_item:
            raise ServiceException(msg="回收站条目不存在")
        trash_dir = cls._get_trash_dir(user_id)
        trash_path = trash_dir / trash_id
        if trash_path.exists():
            if trash_path.is_dir():
                shutil.rmtree(trash_path)
            else:
                trash_path.unlink(missing_ok=True)
        items = [item for item in items if item.get("id") != trash_id]
        cls._save_json(index_path, items)
        return True

    @classmethod
    async def clear_trash(cls, user_id: int) -> int:
        index_path = cls._get_trash_index(user_id)
        items = cls._load_json(index_path, [])
        trash_dir = cls._get_trash_dir(user_id)
        count = 0
        for item in items:
            trash_id = item.get("id")
            if not trash_id:
                continue
            trash_path = trash_dir / trash_id
            if trash_path.exists():
                if trash_path.is_dir():
                    shutil.rmtree(trash_path)
                else:
                    trash_path.unlink(missing_ok=True)
                count += 1
        cls._save_json(index_path, [])
        return count

    @classmethod
    async def create_share(
        cls, path: str, user_id: int, expires_hours: int | None
    ) -> DiskShareEntry:
        target = cls._resolve_path(path, user_id)
        if not target.exists():
            raise ServiceException(msg="文件或目录不存在")
        now = datetime.utcnow()
        expires_at = (
            now + timedelta(hours=expires_hours)
            if expires_hours and expires_hours > 0
            else None
        )
        share_id = uuid4().hex
        entry = DiskShareEntry(
            id=share_id,
            name=target.name or "",
            path=cls._relative_path(target, user_id),
            is_dir=target.is_dir(),
            created_at=now,
            expires_at=expires_at,
        )
        user_path = cls._get_share_dir(user_id) / "shares.json"
        shares = cls._load_json(user_path, [])
        shares.append(
            {
                "id": entry.id,
                "name": entry.name,
                "path": entry.path,
                "is_dir": entry.is_dir,
                "created_at": entry.created_at.isoformat(),
                "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
            }
        )
        cls._save_json(user_path, shares)
        index_path = cls._get_share_index()
        index = cls._load_json(index_path, {})
        index[share_id] = user_id
        cls._save_json(index_path, index)
        return entry

    @classmethod
    async def list_shares(cls, user_id: int) -> DiskShareListOut:
        user_path = cls._get_share_dir(user_id) / "shares.json"
        shares = cls._load_json(user_path, [])
        now = datetime.utcnow()
        entries: list[DiskShareEntry] = []
        valid_items = []
        expired_ids: list[str] = []
        for item in shares:
            share_id = item.get("id")
            if not share_id:
                continue
            expires_at = item.get("expires_at")
            if expires_at:
                expire_dt = cls._parse_datetime(expires_at)
                if expire_dt < now:
                    expired_ids.append(share_id)
                    continue
            entry = DiskShareEntry(
                id=share_id,
                name=item.get("name", ""),
                path=item.get("path", ""),
                is_dir=bool(item.get("is_dir", False)),
                created_at=cls._parse_datetime(item.get("created_at")),
                expires_at=cls._parse_datetime(expires_at) if expires_at else None,
            )
            entries.append(entry)
            valid_items.append(item)
        if expired_ids:
            index_path = cls._get_share_index()
            index = cls._load_json(index_path, {})
            for share_id in expired_ids:
                index.pop(share_id, None)
            cls._save_json(index_path, index)
        if len(valid_items) != len(shares):
            cls._save_json(user_path, valid_items)
        return DiskShareListOut(items=entries)

    @classmethod
    async def revoke_share(cls, share_id: str, user_id: int) -> bool:
        user_path = cls._get_share_dir(user_id) / "shares.json"
        shares = cls._load_json(user_path, [])
        next_shares = [item for item in shares if item.get("id") != share_id]
        if len(next_shares) == len(shares):
            raise ServiceException(msg="分享不存在")
        cls._save_json(user_path, next_shares)
        index_path = cls._get_share_index()
        index = cls._load_json(index_path, {})
        index.pop(share_id, None)
        cls._save_json(index_path, index)
        return True

    @classmethod
    async def resolve_share(cls, share_id: str) -> tuple[int, DiskShareEntry]:
        index_path = cls._get_share_index()
        index = cls._load_json(index_path, {})
        user_id = index.get(share_id)
        if not user_id:
            raise ServiceException(msg="分享不存在或已失效")
        user_path = cls._get_share_dir(int(user_id)) / "shares.json"
        shares = cls._load_json(user_path, [])
        now = datetime.utcnow()
        for item in shares:
            if item.get("id") != share_id:
                continue
            expires_at = item.get("expires_at")
            if expires_at:
                expire_dt = cls._parse_datetime(expires_at)
                if expire_dt < now:
                    await cls.revoke_share(share_id, int(user_id))
                    raise ServiceException(msg="分享已过期")
            entry = DiskShareEntry(
                id=share_id,
                name=item.get("name", ""),
                path=item.get("path", ""),
                is_dir=bool(item.get("is_dir", False)),
                created_at=cls._parse_datetime(item.get("created_at")),
                expires_at=cls._parse_datetime(expires_at) if expires_at else None,
            )
            return int(user_id), entry
        await cls.revoke_share(share_id, int(user_id))
        raise ServiceException(msg="分享不存在或已失效")

    @classmethod
    async def rename(cls, data: DiskRenameIn, user_id: int) -> DiskEntry:
        src = cls._resolve_path(data.src, user_id)
        if not src.exists():
            raise ServiceException(msg="源文件或目录不存在")
        dst = cls._resolve_path(data.dst, user_id)
        if src == dst:
            return cls._to_entry(src, user_id)
        if src == cls._get_user_root(user_id) or dst == cls._get_user_root(user_id):
            raise ServiceException(msg="不允许操作根目录")
        if dst.exists() and not data.overwrite:
            raise ServiceException(msg="目标已存在")
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and data.overwrite:
            if dst.is_dir():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        src.rename(dst)
        return cls._to_entry(dst, user_id)

    @classmethod
    async def create_download_job(cls, path: str, user_id: int, redis) -> str:
        target = cls._resolve_path(path, user_id)
        if not target.exists():
            raise ServiceException(msg="文件或目录不存在")
        if target.is_file():
            raise ServiceException(msg="文件无需打包")
        job_id = uuid4().hex
        key = f"disk:download:{job_id}"
        await redis.hset(
            key,
            mapping={
                "status": "pending",
                "user_id": str(user_id),
                "path": cls._relative_path(target, user_id),
            },
        )
        await redis.expire(key, 10800)
        asyncio.create_task(cls._run_zip_job(job_id, target, user_id, redis))
        return job_id

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
    async def get_download_job_status(
        cls, job_id: str, user_id: int, redis
    ) -> dict:
        key = f"disk:download:{job_id}"
        data = await redis.hgetall(key)
        if not data:
            raise ServiceException(msg="下载任务不存在")
        decoded = DiskService._decode_redis_hash(data)
        if decoded.get("user_id") != str(user_id):
            raise ServiceException(msg="无权访问该任务")
        return {
            "status": decoded.get("status", "pending"),
            "message": decoded.get("error", ""),
            "filename": decoded.get("filename", ""),
        }

    @classmethod
    async def get_download_job_file(
        cls, job_id: str, user_id: int, redis
    ) -> tuple[Path, str]:
        key = f"disk:download:{job_id}"
        data = await redis.hgetall(key)
        if not data:
            raise ServiceException(msg="下载任务不存在")
        decoded = DiskService._decode_redis_hash(data)
        if decoded.get("user_id") != str(user_id):
            raise ServiceException(msg="无权访问该任务")
        if decoded.get("status") != "ready":
            raise ServiceException(msg="任务尚未完成")
        file_path = Path(decoded.get("file_path", ""))
        if not file_path.exists():
            raise ServiceException(msg="压缩文件不存在")
        filename = decoded.get("filename", file_path.name)
        return file_path, filename

    @classmethod
    async def create_download_token(
        cls,
        path: str | None,
        job_id: str | None,
        user_id: int,
        redis,
        ttl_seconds: int = 10800,
    ) -> str:
        if bool(path) == bool(job_id):
            raise ServiceException(msg="必须提供 path 或 job_id")
        if path:
            target = cls._resolve_path(path, user_id)
            if not target.exists():
                raise ServiceException(msg="文件不存在")
            if not target.is_file():
                raise ServiceException(msg="仅支持文件下载令牌")
            payload = {
                "type": "file",
                "user_id": str(user_id),
                "path": cls._relative_path(target, user_id),
            }
        else:
            key = f"disk:download:{job_id}"
            data = await redis.hgetall(key)
            if not data:
                raise ServiceException(msg="下载任务不存在")
            decoded = cls._decode_redis_hash(data)
            if decoded.get("user_id") != str(user_id):
                raise ServiceException(msg="无权访问该任务")
            if decoded.get("status") != "ready":
                raise ServiceException(msg="任务尚未完成")
            payload = {"type": "job", "user_id": str(user_id), "job_id": job_id}
        token = uuid4().hex
        token_key = f"disk:download:token:{token}"
        await redis.hset(token_key, mapping=payload)
        await redis.expire(token_key, ttl_seconds)
        return token

    @classmethod
    async def get_download_token(cls, token: str, redis) -> dict:
        key = f"disk:download:token:{token}"
        data = await redis.hgetall(key)
        if not data:
            raise ServiceException(msg="下载令牌不存在或已过期")
        return cls._decode_redis_hash(data)

    @classmethod
    async def _run_zip_job(
        cls, job_id: str, target: Path, user_id: int, redis
    ) -> None:
        key = f"disk:download:{job_id}"
        try:
            zip_path = await cls._zip_dir(target, user_id)
            filename = f"{(target.name or 'root')}.zip"
            await redis.hset(
                key,
                mapping={
                    "status": "ready",
                    "file_path": str(zip_path),
                    "filename": filename,
                },
            )
            await redis.expire(key, 10800)
            asyncio.create_task(cls._cleanup_job_file(zip_path, key, redis, 10800))
        except Exception as exc:
            await redis.hset(
                key,
                mapping={"status": "error", "error": str(exc)},
            )
            await redis.expire(key, 600)

    @classmethod
    async def _cleanup_job_file(
        cls, zip_path: Path, key: str, redis, delay: int
    ) -> None:
        await asyncio.sleep(delay)
        try:
            zip_path.unlink(missing_ok=True)
        except OSError:
            pass
        try:
            await redis.delete(key)
        except Exception:
            return
