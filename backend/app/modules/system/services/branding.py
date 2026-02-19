from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.exception import ServiceException
from app.modules.system.services.config import ConfigCenterService
from app.modules.system.typed.keys import ConfigKey


class BrandingService:
    ASSET_SPEC = {
        "logo": {
            "config_key": ConfigKey.SYSTEM_SITE_LOGO_URL,
            "allowed_mime": {"image/png", "image/jpeg", "image/webp", "image/svg+xml"},
            "max_size": 2 * 1024 * 1024,
            "subdir": "site-logo",
        },
        "favicon": {
            "config_key": ConfigKey.SYSTEM_SITE_FAVICON_URL,
            "allowed_mime": {
                "image/png",
                "image/x-icon",
                "image/vnd.microsoft.icon",
                "image/svg+xml",
            },
            "max_size": 512 * 1024,
            "subdir": "site-favicon",
        },
        "login_bg": {
            "config_key": ConfigKey.SYSTEM_LOGIN_BACKGROUND_URL,
            "allowed_mime": {"image/png", "image/jpeg", "image/webp"},
            "max_size": 5 * 1024 * 1024,
            "subdir": "login-bg",
        },
        "theme_image": {
            "config_key": ConfigKey.SYSTEM_THEME_IMAGE_URL,
            "allowed_mime": {"image/png", "image/jpeg", "image/webp", "image/svg+xml"},
            "max_size": 5 * 1024 * 1024,
            "subdir": "theme-image",
        },
    }

    @classmethod
    async def upload_site_asset(
        cls,
        *,
        db: AsyncSession,
        upload: UploadFile,
        asset_type: str,
        updated_by: int | None,
    ) -> dict[str, str]:
        spec = cls.ASSET_SPEC.get(asset_type)
        if not spec:
            raise ServiceException(msg="不支持的站点资源类型")

        mime = (upload.content_type or "").strip().lower()
        if mime not in spec["allowed_mime"]:
            raise ServiceException(msg="文件格式不支持")

        original_name = (upload.filename or "asset").strip() or "asset"
        ext = Path(original_name).suffix.lower() or cls._ext_from_mime(mime)
        if not ext:
            raise ServiceException(msg="文件后缀不合法")

        file_bytes = await upload.read()
        await upload.close()
        if not file_bytes:
            raise ServiceException(msg="上传文件为空")
        if len(file_bytes) > int(spec["max_size"]):
            raise ServiceException(msg="上传文件超过大小限制")

        digest = hashlib.sha1(file_bytes).hexdigest()
        asset_id = uuid4().hex

        static_dir = (Path.cwd() / "app" / "static" / "branding" / spec["subdir"]).resolve()
        static_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"{asset_id}{ext}"
        target_path = (static_dir / file_name).resolve()
        if not str(target_path).startswith(str(static_dir)):
            raise ServiceException(msg="资源存储路径非法")
        target_path.write_bytes(file_bytes)

        cls._prune_history(static_dir, keep=3)

        asset_url = f"{settings.APP_API_PREFIX}/static/branding/{spec['subdir']}/{file_name}?v={digest}"
        cfg = ConfigCenterService(db)
        await cfg.update_batch(
            items=[{"key": str(spec["config_key"]), "value": asset_url}],
            updated_by=updated_by,
        )
        return {"asset_id": asset_id, "asset_url": asset_url}

    @staticmethod
    def _ext_from_mime(mime: str) -> str:
        mapping = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/webp": ".webp",
            "image/svg+xml": ".svg",
            "image/x-icon": ".ico",
            "image/vnd.microsoft.icon": ".ico",
        }
        return mapping.get(mime, "")

    @staticmethod
    def _prune_history(branding_dir: Path, keep: int = 3) -> None:
        files = [f for f in branding_dir.iterdir() if f.is_file()]
        files.sort(key=lambda item: item.stat().st_mtime, reverse=True)
        for stale in files[keep:]:
            try:
                stale.unlink(missing_ok=True)
            except OSError:
                continue

