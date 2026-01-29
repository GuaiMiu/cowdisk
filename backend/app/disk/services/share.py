"""
@File: share.py
@Author: GuaiMiu
@Date: 2026/1/24
@Version: 1.0
@Description: 分享服务
"""

from datetime import datetime, timedelta
from pathlib import Path
from pathlib import PurePosixPath

from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.exception import ServiceException
from app.disk.models.share import Share
from app.admin.dao.user import user_crud
from app.disk.services.disk import DiskService


class ShareService:
    """分享服务类"""

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
            "path": share.path,
            "token": share.token,
            "name": share.name,
            "createdAt": cls._to_ms(share.created_at),
            "expiresAt": cls._to_ms(share.expires_at) if share.expires_at else None,
            "hasCode": bool(share.code),
            "code": share.code if include_code else None,
            "status": share.status,
        }

    @staticmethod
    def _share_resource_exists(share: Share, user_id: int) -> bool:
        try:
            target = DiskService._resolve_path(share.path, user_id)
        except ServiceException:
            return False
        if not target.exists():
            return False
        if share.resource_type == "FILE" and not target.is_file():
            return False
        if share.resource_type == "FOLDER" and not target.is_dir():
            return False
        return True

    @staticmethod
    async def create_share(
        user_id: int,
        resource_type: str,
        path: str,
        expires_in_days: int | None,
        expires_at: int | None,
        code: str | None,
        db: AsyncSession,
    ) -> dict:
        target = DiskService._resolve_path(path, user_id)
        if not target.exists():
            raise ServiceException(msg="文件或目录不存在")
        if resource_type not in {"FILE", "FOLDER"}:
            raise ServiceException(msg="资源类型不合法")
        if resource_type == "FILE" and target.is_dir():
            raise ServiceException(msg="资源类型不匹配")
        if resource_type == "FOLDER" and target.is_file():
            raise ServiceException(msg="资源类型不匹配")
        if code and not (code.isdigit() and len(code) == 4):
            raise ServiceException(msg="提取码需为 4 位数字")
        now = datetime.utcnow()
        if expires_at:
            expires_dt = datetime.utcfromtimestamp(expires_at / 1000)
            if expires_dt <= now:
                raise ServiceException(msg="有效期必须晚于当前时间")
            resolved_expires_at = expires_dt
        elif expires_in_days:
            resolved_expires_at = now + timedelta(days=expires_in_days)
        else:
            resolved_expires_at = None
        share = Share(
            user_id=user_id,
            resource_type=resource_type,
            path=DiskService._relative_path(target, user_id),
            name=target.name or "root",
            expires_at=resolved_expires_at,
            code=code,
            status=1,
        )
        db.add(share)
        await db.commit()
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
        now = datetime.utcnow()
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
            count_query = count_query.where((Share.expires_at.is_(None)) | (Share.expires_at > now))
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
            missing_rows = [
                row for row in rows_all if not ShareService._share_resource_exists(row, user_id)
            ]
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
            if not ShareService._share_resource_exists(row, user_id):
                item["status"] = -1
                item["missing"] = True
            else:
                item["missing"] = False
            items.append(item)
        return items, total, pages, size

    @staticmethod
    async def revoke_share(user_id: int, share_id: str, db: AsyncSession) -> None:
        result = await db.exec(
            select(Share).where(Share.user_id == user_id, Share.id == share_id, Share.is_deleted == False)
        )
        share = result.first()
        if not share:
            raise ServiceException(msg="分享不存在")
        share.status = 0
        db.add(share)
        await db.commit()

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
            select(Share).where(Share.user_id == user_id, Share.id == share_id, Share.is_deleted == False)
        )
        share = result.first()
        if not share:
            raise ServiceException(msg="分享不存在")
        now = datetime.utcnow()
        if expires_at is not None or expires_in_days is not None:
            if expires_at:
                expires_dt = datetime.utcfromtimestamp(expires_at / 1000)
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
    async def resolve_share(token: str, db: AsyncSession) -> tuple[int, dict]:
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
        if not ShareService._share_resource_exists(share, share.user_id):
            raise ServiceException(msg="分享文件已被删除")
        now = datetime.utcnow()
        if share.expires_at and share.expires_at <= now:
            share.status = 0
            db.add(share)
            await db.commit()
            raise ServiceException(msg="该分享已过期")
        data = ShareService._share_model_to_dict(share, include_code=True)
        owner = await user_crud.get_by_id(db, share.user_id)
        owner_name = None
        if owner:
            owner_name = owner.nickname or owner.username
        data["ownerName"] = owner_name
        return share.user_id, data

    @staticmethod
    async def delete_share(user_id: int, share_id: str, db: AsyncSession) -> None:
        result = await db.exec(
            select(Share).where(Share.user_id == user_id, Share.id == share_id, Share.is_deleted == False)
        )
        share = result.first()
        if not share:
            raise ServiceException(msg="分享不存在")
        share.is_deleted = True
        db.add(share)
        await db.commit()

    @staticmethod
    def share_base_path(share: dict, user_id: int) -> Path:
        return DiskService._resolve_path(share.get("path", ""), user_id)

    @staticmethod
    def resolve_share_child(base: Path, child_path: str | None) -> Path:
        rel = PurePosixPath(child_path or "")
        if rel.is_absolute() or ".." in rel.parts:
            raise ServiceException(msg="非法路径")
        resolved = (base / Path(*rel.parts)).resolve()
        if not resolved.is_relative_to(base):
            raise ServiceException(msg="非法路径")
        return resolved

    @staticmethod
    def to_share_entry(base: Path, item: Path) -> dict:
        stat = item.stat()
        rel = item.relative_to(base).as_posix() if item != base else ""
        return {
            "name": item.name,
            "path": rel,
            "is_dir": item.is_dir(),
            "size": 0 if item.is_dir() else stat.st_size,
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

    @classmethod
    async def list_share_entries(
        cls, share: dict, user_id: int, path: str | None
    ) -> list[dict]:
        base = cls.share_base_path(share, user_id)
        if share.get("resourceType") != "FOLDER":
            raise ServiceException(msg="分享不是目录")
        target = cls.resolve_share_child(base, path)
        if not target.exists() or not target.is_dir():
            raise ServiceException(msg="目录不存在")
        items = [cls.to_share_entry(base, child) for child in target.iterdir()]
        items.sort(key=lambda entry: (not entry["is_dir"], entry["name"].lower()))
        return items

    @classmethod
    async def download_share_file(
        cls, share: dict, user_id: int, path: str | None
    ) -> Path:
        base = cls.share_base_path(share, user_id)
        if share.get("resourceType") == "FILE":
            return base
        target = cls.resolve_share_child(base, path)
        if not target.exists() or not target.is_file():
            raise ServiceException(msg="文件不存在")
        return target

    @staticmethod
    async def save_share_to_user(
        share: dict,
        owner_id: int,
        target_user_id: int,
        target_path: str,
    ) -> None:
        base = ShareService.share_base_path(share, owner_id)
        dest_dir = DiskService._resolve_path(target_path, target_user_id)
        if not dest_dir.exists() or not dest_dir.is_dir():
            raise ServiceException(msg="目标目录不存在")
        if share.get("resourceType") == "FILE":
            dest = DiskService._unique_path(dest_dir / base.name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(base.read_bytes())
            return
        dest = DiskService._unique_path(dest_dir / (base.name or "share"))
        if dest.exists():
            raise ServiceException(msg="目标路径冲突")
        dest.mkdir(parents=True, exist_ok=True)
        for item in base.rglob("*"):
            relative = item.relative_to(base)
            target_item = dest / relative
            if item.is_dir():
                target_item.mkdir(parents=True, exist_ok=True)
            else:
                target_item.parent.mkdir(parents=True, exist_ok=True)
                target_item.write_bytes(item.read_bytes())
