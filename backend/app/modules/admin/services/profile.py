from __future__ import annotations

import asyncio
import hashlib
import mimetypes
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.core.errors.exceptions import BadRequestException, PayloadTooLarge
from app.modules.admin.models.user import User


class ProfileService:
    ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp"}
    MAX_AVATAR_SIZE = 2 * 1024 * 1024
    DEFAULT_AVATAR_PATH = "avatar/default.jpg"

    @classmethod
    async def save_avatar(cls, *, user: User, upload: UploadFile) -> dict[str, str]:
        mime = (upload.content_type or "").strip().lower()
        if mime not in cls.ALLOWED_MIME:
            raise BadRequestException("头像仅支持 PNG/JPEG/WEBP")

        payload = await upload.read()
        await upload.close()
        if not payload:
            raise BadRequestException("上传文件为空")
        if len(payload) > cls.MAX_AVATAR_SIZE:
            raise PayloadTooLarge("头像文件不能超过 2MB")

        suffix = cls._suffix_from_mime(mime)
        digest = hashlib.sha1(payload).hexdigest()
        file_name = f"{uuid4().hex}{suffix}"
        relative_dir = Path("avatar") / str(user.id)
        relative_path = relative_dir / file_name

        static_root = cls._static_root()
        target_dir = (static_root / relative_dir).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)
        target = (target_dir / file_name).resolve()
        cls._ensure_under_root(target, static_root)

        await asyncio.to_thread(target.write_bytes, payload)
        await cls.delete_avatar_file(user.avatar_path)
        user.avatar_path = relative_path.as_posix()

        return {
            "avatar_path": user.avatar_path,
            "avatar_url": cls.avatar_url(user.avatar_path, digest),
        }

    @classmethod
    async def delete_avatar_file(cls, avatar_path: str | None) -> None:
        if not avatar_path:
            return
        clean = avatar_path.strip().lstrip("/")
        if not clean or clean == cls.DEFAULT_AVATAR_PATH:
            return
        if not clean.startswith("avatar/"):
            return
        static_root = cls._static_root()
        target = (static_root / clean).resolve()
        cls._ensure_under_root(target, static_root)
        if target.exists() and target.is_file():
            await asyncio.to_thread(target.unlink, True)

    @classmethod
    def resolve_avatar_file(cls, avatar_path: str | None) -> tuple[Path | None, str | None]:
        if not avatar_path:
            return None, None
        clean = avatar_path.strip().lstrip("/")
        if not clean:
            return None, None
        static_root = cls._static_root()
        target = (static_root / clean).resolve()
        cls._ensure_under_root(target, static_root)
        if not target.exists() or not target.is_file():
            return None, None
        content_type, _ = mimetypes.guess_type(str(target))
        return target, content_type or "application/octet-stream"

    @staticmethod
    def _suffix_from_mime(mime: str) -> str:
        mapping = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/webp": ".webp",
        }
        return mapping.get(mime, ".bin")

    @staticmethod
    def _static_root() -> Path:
        root = (Path.cwd() / "app" / "static").resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    @staticmethod
    def _ensure_under_root(target: Path, root: Path) -> None:
        if not str(target).startswith(str(root)):
            raise BadRequestException("头像路径非法")

    @staticmethod
    def avatar_url(avatar_path: str, digest: str | None = None) -> str:
        suffix = f"?v={digest}" if digest else ""
        return f"{settings.APP_API_PREFIX}/static/{avatar_path}{suffix}"
