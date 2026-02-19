"""
@File: share.py
@Author: GuaiMiu
@Date: 2026/1/24
@Version: 1.0
@Description: 分享服务
"""

from datetime import datetime, timedelta
from pathlib import PurePosixPath
import mimetypes
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.exception import ServiceException
from app.modules.disk.models.share import Share
from app.modules.admin.dao.user import user_crud
from app.modules.disk.models.file import File
from app.modules.disk.services.file import FileService
from app.modules.disk.storage.backends import get_storage_backend
from app.audit.decorator import audited


class ShareService:
    """分享服务类"""

    @staticmethod
    def _audit_share_detail(share: dict | None) -> dict:
        if not share:
            return {}
        return {
            "resource_id": str(share.get("id") or ""),
            "resource_type": "SHARE",
            "path": share.get("name"),
            "detail": {
                "share_id": share.get("id"),
                "file_id": share.get("fileId"),
                "resource_type": share.get("resourceType"),
            },
        }

    @staticmethod
    async def _extract_share_from_result(*_args, **_kwargs):
        result = _kwargs.get("result")
        if isinstance(result, dict):
            return ShareService._audit_share_detail(result)
        if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], dict):
            return ShareService._audit_share_detail(result[1])
        return {}

    @staticmethod
    def share_access_key(token: str, access_token: str) -> str:
        return f"share:access:{token}:{access_token}"

    @staticmethod
    def _to_ms(dt: datetime) -> int:
        return int(dt.timestamp() * 1000)

    @classmethod
    def _share_model_to_dict(cls, share: Share, include_code: bool = True) -> dict:
        return {
            "id": share.id,
            "resourceType": share.resource_type,
            "fileId": share.file_id,
            "token": share.token,
            "name": share.name,
            "createdAt": cls._to_ms(share.created_at),
            "expiresAt": cls._to_ms(share.expires_at) if share.expires_at else None,
            "hasCode": bool(share.code),
            "code": share.code if include_code else None,
            "status": share.status,
        }

    @staticmethod
    async def _share_resource_exists(
        share: Share, user_id: int, db: AsyncSession
    ) -> bool:
        stmt = select(File).where(
            File.id == share.file_id,
            File.user_id == user_id,
            File.is_deleted == False,
        )
        target = (await db.exec(stmt)).first()
        if not target:
            return False
        if share.resource_type == "FILE" and target.is_dir:
            return False
        if share.resource_type == "FOLDER" and not target.is_dir:
            return False
        return True

    @staticmethod
    @staticmethod
    @audited(
        "SHARE_CREATE",
        resource_type="SHARE",
        extractors=[_extract_share_from_result],
        auto_commit=True,
    )
    async def create_share(
        user_id: int,
        file_id: int,
        expires_in_days: int | None,
        expires_at: int | None,
        code: str | None,
        db: AsyncSession,
        commit: bool = True,
    ) -> dict:
        stmt = select(File).where(
            File.id == file_id,
            File.user_id == user_id,
            File.is_deleted == False,
        )
        target = (await db.exec(stmt)).first()
        if not target:
            raise ServiceException(msg="文件或目录不存在")
        if code and not (code.isdigit() and len(code) == 4):
            raise ServiceException(msg="提取码需为 4 位数字")
        now = ShareService._now()
        if expires_at:
            expires_dt = datetime.fromtimestamp(expires_at / 1000)
            if expires_dt <= now:
                raise ServiceException(msg="有效期必须晚于当前时间")
            resolved_expires_at = expires_dt
        elif expires_in_days:
            resolved_expires_at = now + timedelta(days=expires_in_days)
        else:
            resolved_expires_at = None
        resource_type = "FOLDER" if target.is_dir else "FILE"
        share = Share(
            user_id=user_id,
            resource_type=resource_type,
            file_id=target.id,
            path="",
            name=target.name or "root",
            expires_at=resolved_expires_at,
            code=code,
            status=1,
        )
        db.add(share)
        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(share)
        return ShareService._share_model_to_dict(share, include_code=True)

    @staticmethod
    async def list_shares(
        user_id: int,
        keyword: str | None,
        status: str | None,
        page: int,
        size: int,
        db: AsyncSession,
    ) -> tuple[list[dict], int, int, int]:
        page = max(page, 1)
        size = max(1, min(size, 100))
        now = ShareService._now()
        base_filter = (Share.user_id == user_id, Share.is_deleted == False)
        query = select(Share).where(*base_filter)
        count_query = select(func.count()).select_from(Share).where(*base_filter)
        if keyword:
            query = query.where(Share.name.contains(keyword))
            count_query = count_query.where(Share.name.contains(keyword))
        if status == "active":
            query = query.where(Share.status == 1)
            query = query.where((Share.expires_at.is_(None)) | (Share.expires_at > now))
            count_query = count_query.where(Share.status == 1)
            count_query = count_query.where(
                (Share.expires_at.is_(None)) | (Share.expires_at > now)
            )
        elif status == "expired":
            query = query.where(Share.status == 1)
            query = query.where(Share.expires_at.is_not(None))
            query = query.where(Share.expires_at <= now)
            count_query = count_query.where(Share.status == 1)
            count_query = count_query.where(Share.expires_at.is_not(None))
            count_query = count_query.where(Share.expires_at <= now)
        query = query.order_by(Share.created_at.desc())
        offset = (page - 1) * size
        if status == "missing":
            result_all = await db.exec(query)
            rows_all = result_all.all()
            missing_rows = []
            for row in rows_all:
                if not await ShareService._share_resource_exists(row, user_id, db):
                    missing_rows.append(row)
            total = len(missing_rows)
            pages = max((total + size - 1) // size, 1) if total > 0 else 0
            rows = missing_rows[offset : offset + size]
            items: list[dict] = []
            for row in rows:
                item = ShareService._share_model_to_dict(row, include_code=True)
                item["status"] = -1
                item["missing"] = True
                items.append(item)
            return items, total, pages, size
        result_total = await db.exec(count_query)
        total = int(result_total.one() or 0)
        pages = max((total + size - 1) // size, 1) if total > 0 else 0
        result = await db.exec(query.offset(offset).limit(size))
        rows = result.all()
        items = []
        for row in rows:
            item = ShareService._share_model_to_dict(row, include_code=True)
            if not await ShareService._share_resource_exists(row, user_id, db):
                item["status"] = -1
                item["missing"] = True
            else:
                item["missing"] = False
            items.append(item)
        return items, total, pages, size

    @staticmethod
    async def revoke_share(user_id: int, share_id: str, db: AsyncSession) -> None:
        result = await db.exec(
            select(Share).where(
                Share.user_id == user_id,
                Share.id == share_id,
                Share.is_deleted == False,
            )
        )
        share = result.first()
        if not share:
            raise ServiceException(msg="分享不存在")
        share.status = 0
        db.add(share)
        await db.commit()

    @staticmethod
    async def batch_update_status(
        user_id: int, ids: list[str], status: int, db: AsyncSession
    ) -> dict:
        if status not in (0, 1):
            raise ServiceException(msg="状态值不合法")
        if not ids:
            return {"success": 0, "failed": []}
        result = await db.exec(
            select(Share).where(
                Share.user_id == user_id, Share.id.in_(ids), Share.is_deleted == False
            )
        )
        rows = result.all()
        found_ids = {row.id for row in rows}
        for row in rows:
            row.status = status
            db.add(row)
        await db.commit()
        failed = [share_id for share_id in ids if share_id not in found_ids]
        return {"success": len(found_ids), "failed": failed}

    @staticmethod
    async def update_share(
        user_id: int,
        share_id: str,
        expires_in_days: int | None,
        expires_at: int | None,
        code: str | None,
        status: int | None,
        db: AsyncSession,
    ) -> dict:
        result = await db.exec(
            select(Share).where(
                Share.user_id == user_id,
                Share.id == share_id,
                Share.is_deleted == False,
            )
        )
        share = result.first()
        if not share:
            raise ServiceException(msg="分享不存在")
        now = ShareService._now()
        if expires_at is not None or expires_in_days is not None:
            if expires_at:
                expires_dt = datetime.fromtimestamp(expires_at / 1000)
                if expires_dt <= now:
                    raise ServiceException(msg="有效期必须晚于当前时间")
                share.expires_at = expires_dt
            elif expires_in_days is None or expires_in_days <= 0:
                share.expires_at = None
            else:
                share.expires_at = now + timedelta(days=expires_in_days)
        if code is not None:
            cleaned = code.strip()
            if cleaned:
                if not (cleaned.isdigit() and len(cleaned) == 4):
                    raise ServiceException(msg="提取码需为 4 位数字")
                share.code = cleaned
            else:
                share.code = None
        if status is not None:
            share.status = status
        db.add(share)
        await db.commit()
        await db.refresh(share)
        return ShareService._share_model_to_dict(share, include_code=True)

    @staticmethod
    @staticmethod
    @audited(
        "SHARE_ACCESS",
        resource_type="SHARE",
        extractors=[_extract_share_from_result],
        auto_commit=True,
    )
    async def resolve_share(
        token: str, db: AsyncSession, commit: bool = False
    ) -> tuple[int, dict]:
        result = await db.exec(select(Share).where(Share.token == token))
        share = result.first()
        if not share:
            raise ServiceException(msg="该分享不存在")
        if share.is_deleted:
            raise ServiceException(msg="该分享已删除")
        if share.status == 0:
            raise ServiceException(msg="该分享已取消")
        if share.is_deleted:
            raise ServiceException(msg="该分享已删除")
        if not await ShareService._share_resource_exists(share, share.user_id, db):
            raise ServiceException(msg="分享文件已被删除")
        now = ShareService._now()
        if share.expires_at and ShareService._as_local(share.expires_at) <= now:
            share.status = 0
            db.add(share)
            if commit:
                await db.commit()
            else:
                await db.flush()
            raise ServiceException(msg="该分享已过期")
        data = ShareService._share_model_to_dict(share, include_code=True)
        owner = await user_crud.get_by_id(db, share.user_id)
        owner_name = None
        if owner:
            owner_name = owner.nickname or owner.username
        data["ownerName"] = owner_name
        return share.user_id, data

    @staticmethod
    async def batch_delete(user_id: int, ids: list[str], db: AsyncSession) -> dict:
        if not ids:
            return {"success": 0, "failed": []}
        result = await db.exec(
            select(Share).where(
                Share.user_id == user_id, Share.id.in_(ids), Share.is_deleted == False
            )
        )
        rows = result.all()
        found_ids = {row.id for row in rows}
        for row in rows:
            row.is_deleted = True
            db.add(row)
        await db.commit()
        failed = [share_id for share_id in ids if share_id not in found_ids]
        return {"success": len(found_ids), "failed": failed}

    @staticmethod
    async def delete_share(user_id: int, share_id: str, db: AsyncSession) -> None:
        result = await db.exec(
            select(Share).where(
                Share.user_id == user_id,
                Share.id == share_id,
                Share.is_deleted == False,
            )
        )
        share = result.first()
        if not share:
            raise ServiceException(msg="分享不存在")
        share.is_deleted = True
        db.add(share)
        await db.commit()

    @staticmethod
    async def _get_share_root_file(share: dict, user_id: int, db: AsyncSession) -> File:
        stmt = select(File).where(
            File.id == share.get("fileId"),
            File.user_id == user_id,
            File.is_deleted == False,
        )
        target = (await db.exec(stmt)).first()
        if not target:
            raise ServiceException(msg="分享文件已被删除")
        return target

    @staticmethod
    def _to_entry(file: File) -> dict:
        return {
            "id": file.id,
            "name": file.name,
            "parent_id": file.parent_id,
            "is_dir": file.is_dir,
            "size": file.size,
            "mime_type": file.mime_type,
            "updated_at": file.updated_at.isoformat() if file.updated_at else None,
        }

    @classmethod
    async def list_share_entries(
        cls,
        share: dict,
        user_id: int,
        db: AsyncSession,
        parent_id: int | None,
    ) -> list[dict]:
        if share.get("resourceType") != "FOLDER":
            raise ServiceException(msg="分享不是目录")
        root = await cls._get_share_root_file(share, user_id, db)
        target_parent_id = parent_id if parent_id is not None else root.id
        if target_parent_id != root.id:
            if not await FileService._is_descendant(
                db, user_id, target_parent_id, root.id
            ):
                raise ServiceException(msg="目录不在分享范围内")
        stmt = (
            select(File)
            .where(
                File.user_id == user_id,
                File.parent_id == target_parent_id,
                File.is_deleted == False,
            )
            .order_by(File.is_dir.desc(), File.name.asc())
        )
        rows = (await db.exec(stmt)).all()
        return [cls._to_entry(item) for item in rows]

    @classmethod
    async def get_share_file_meta(
        cls, share: dict, user_id: int, db: AsyncSession
    ) -> dict | None:
        if share.get("resourceType") != "FILE":
            return None
        target = await cls._get_share_root_file(share, user_id, db)
        mime = target.mime_type or mimetypes.guess_type(target.name)[0]
        return {
            "size": target.size,
            "mime": mime or "application/octet-stream",
        }

    @classmethod
    async def download_share_file(
        cls,
        share: dict,
        user_id: int,
        db: AsyncSession,
        file_id: int | None,
    ) -> Path:
        root = await cls._get_share_root_file(share, user_id, db)
        target = root
        if share.get("resourceType") == "FOLDER":
            if not file_id:
                raise ServiceException(msg="缺少文件ID")
            if not await FileService._is_descendant(db, user_id, file_id, root.id):
                raise ServiceException(msg="文件不在分享范围内")
            stmt = select(File).where(
                File.id == file_id,
                File.user_id == user_id,
                File.is_deleted == False,
            )
            target = (await db.exec(stmt)).first()
            if not target or target.is_dir:
                raise ServiceException(msg="文件不存在")
        if target.is_dir:
            raise ServiceException(msg="不能下载目录")
        storage = await FileService._get_storage_by_id(db, target.storage_id)
        backend = get_storage_backend(storage)
        return backend.resolve_abs_path(target.storage_path)

    @staticmethod
    async def save_share_to_user(
        share: dict,
        owner_id: int,
        target_user_id: int,
        target_parent_id: int | None,
        db: AsyncSession,
    ) -> None:
        root = await ShareService._get_share_root_file(share, owner_id, db)
        parent = None
        if target_parent_id is not None:
            parent = await FileService._get_active_dir(
                db, target_user_id, target_parent_id
            )
        storage = await FileService.get_default_storage(db)
        if parent and parent.storage_id != storage.id:
            raise ServiceException(msg="目标目录存储不一致")
        backend = get_storage_backend(storage)

        if not root.is_dir:
            await FileService._ensure_unique_name(
                db, target_user_id, target_parent_id, root.name
            )
            storage_path = FileService._storage_path_for(
                target_user_id, parent, root.name
            )
            await backend.ensure_dir(PurePosixPath(storage_path).parent.as_posix())
            await backend.copy_file(root.storage_path, storage_path)
            entry = File(
                user_id=target_user_id,
                parent_id=target_parent_id,
                name=root.name,
                is_dir=False,
                size=root.size,
                mime_type=root.mime_type,
                etag=root.etag,
                storage_id=storage.id,
                storage_path=storage_path,
                storage_path_hash=FileService._hash_storage_path(storage_path),
                content_hash=root.content_hash,
                is_deleted=False,
                deleted_at=None,
            )
            db.add(entry)
            await db.commit()
            return

        root_dir = await FileService.create_dir(
            db=db,
            user_id=target_user_id,
            parent_id=target_parent_id,
            name=root.name,
        )
        id_map: dict[int, int] = {root.id: root_dir.id}
        queue = [root.id]
        while queue:
            stmt = (
                select(File)
                .where(
                    File.user_id == owner_id,
                    File.parent_id.in_(queue),
                    File.is_deleted == False,
                )
                .order_by(File.is_dir.desc(), File.name.asc())
            )
            children = (await db.exec(stmt)).all()
            if not children:
                break
            next_queue: list[int] = []
            for child in children:
                new_parent_id = id_map.get(child.parent_id or root.id)
                new_parent = await FileService._get_active_dir(
                    db, target_user_id, new_parent_id
                )
                if child.is_dir:
                    created = await FileService.create_dir(
                        db=db,
                        user_id=target_user_id,
                        parent_id=new_parent_id,
                        name=child.name,
                    )
                    id_map[child.id] = created.id
                    next_queue.append(child.id)
                else:
                    storage_path = FileService._storage_path_for(
                        target_user_id, new_parent, child.name
                    )
                    await backend.copy_file(child.storage_path, storage_path)
                    entry = File(
                        user_id=target_user_id,
                        parent_id=new_parent_id,
                        name=child.name,
                        is_dir=False,
                        size=child.size,
                        mime_type=child.mime_type,
                        etag=child.etag,
                        storage_id=storage.id,
                        storage_path=storage_path,
                        storage_path_hash=FileService._hash_storage_path(storage_path),
                        content_hash=child.content_hash,
                        is_deleted=False,
                        deleted_at=None,
                    )
                    db.add(entry)
            await db.commit()
            queue = next_queue

    @staticmethod
    def _now() -> datetime:
        return datetime.now()

    @staticmethod
    def _as_local(dt: datetime) -> datetime:
        return dt
