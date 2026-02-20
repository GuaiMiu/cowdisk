"""
@File: office.py
@Author: GuaiMiu
@Date: 2026/2/15
@Version: 1.0
@Description: Office/WOPI 服务
"""

from __future__ import annotations

import asyncio
import json
import mimetypes
import re
import secrets
import ssl
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlencode, urlparse

from fastapi import Request
from starlette.responses import FileResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.errors.exceptions import (
    BadRequestException,
    OfficeForbidden,
    OfficeTokenExpired,
    OfficeTokenInvalid,
    OfficeUnavailable,
    PreviewNotSupported,
    ThumbnailNotSupported,
)
from app.modules.admin.models.user import User
from app.modules.admin.services.profile import ProfileService
from app.modules.disk.models.file import File
from app.modules.disk.services.file import FileService
from app.modules.disk.storage.backends import get_storage_backend


class OfficeService:
    _OFFICE_EXTENSIONS = {
        "doc",
        "docx",
        "rtf",
        "xls",
        "xlsx",
        "csv",
        "ppt",
        "pptx",
        "odp",
        "ods",
        "odt",
    }
    _COLLABORA_DISCOVERY_CACHE_TTL = 300
    _collabora_discovery_cache: dict[str, tuple[float, dict[str, str]]] = {}
    _collabora_discovery_lock = asyncio.Lock()

    @classmethod
    def _is_office_file(cls, entry: File) -> bool:
        if entry.is_dir:
            return False
        suffix = Path(entry.name or "").suffix.lower().lstrip(".")
        return suffix in cls._OFFICE_EXTENSIONS

    @staticmethod
    def _absolute_url_from_path(request: Request, relative_or_absolute: str) -> str:
        value = (relative_or_absolute or "").strip()
        if value.startswith("http://") or value.startswith("https://"):
            return value
        base = str(request.base_url).rstrip("/")
        if not value.startswith("/"):
            value = f"/{value}"
        return f"{base}{value}"

    @staticmethod
    def _join_base_with_path(base_url: str, path: str) -> str:
        base = (base_url or "").strip().rstrip("/")
        p = (path or "").strip()
        if not p.startswith("/"):
            p = f"/{p}"
        return f"{base}{p}"

    @staticmethod
    def _normalize_lang(value: str | None) -> str | None:
        if not value:
            return None
        raw = value.strip().replace("_", "-")
        if not raw:
            return None
        # zh / zh-CN / en-US 这类格式
        if not re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", raw):
            return None
        parts = raw.split("-")
        primary = parts[0].lower()
        if len(parts) == 1:
            return primary
        tail = "-".join(part.upper() if len(part) == 2 else part for part in parts[1:])
        return f"{primary}-{tail}"

    @classmethod
    async def _resolve_office_lang(cls, request: Request, cfg, lang: str | None) -> str:
        direct = cls._normalize_lang(lang)
        if direct:
            return direct
        accept = (request.headers.get("accept-language") or "").split(",")[0].split(";")[0].strip()
        accept_lang = cls._normalize_lang(accept)
        if accept_lang:
            return accept_lang
        default_locale = await cfg.system.default_locale()
        normalized_default = cls._normalize_lang(default_locale)
        return normalized_default or "en-US"

    @staticmethod
    async def _fetch_collabora_discovery(
        collabora_url: str,
        *,
        verify_tls: bool,
        timeout_seconds: int,
    ) -> str:
        url = f"{collabora_url.rstrip('/')}/hosting/discovery"

        def _sync_fetch() -> str:
            context = None
            if not verify_tls:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(url, timeout=timeout_seconds, context=context) as resp:
                body = resp.read()
            return body.decode("utf-8", errors="replace")

        return await asyncio.to_thread(_sync_fetch)

    @classmethod
    async def _get_collabora_urlsrc_map(
        cls,
        collabora_url: str,
        *,
        verify_tls: bool,
        timeout_seconds: int,
    ) -> dict[str, str]:
        cache_key = collabora_url.rstrip("/")
        now = time.time()
        cached = cls._collabora_discovery_cache.get(cache_key)
        if cached and cached[0] > now:
            return cached[1]

        async with cls._collabora_discovery_lock:
            cached = cls._collabora_discovery_cache.get(cache_key)
            if cached and cached[0] > now:
                return cached[1]
            xml_text = await cls._fetch_collabora_discovery(
                collabora_url=cache_key,
                verify_tls=verify_tls,
                timeout_seconds=timeout_seconds,
            )
            root = ET.fromstring(xml_text)
            best_by_ext: dict[str, tuple[int, str]] = {}
            priority = {"edit": 0, "view": 1, "view_comment": 2}
            for elem in root.iter():
                if not str(elem.tag).lower().endswith("action"):
                    continue
                ext = (elem.attrib.get("ext") or "").strip().lower()
                name = (elem.attrib.get("name") or "").strip().lower()
                urlsrc = (elem.attrib.get("urlsrc") or "").strip()
                if not ext or not urlsrc:
                    continue
                score = priority.get(name, 99)
                existing = best_by_ext.get(ext)
                if existing is None or score < existing[0]:
                    best_by_ext[ext] = (score, urlsrc)
            urlsrc_map = {ext: value[1] for ext, value in best_by_ext.items()}
            cls._collabora_discovery_cache[cache_key] = (
                now + cls._COLLABORA_DISCOVERY_CACHE_TTL,
                urlsrc_map,
            )
            return urlsrc_map

    @classmethod
    async def issue_wopi_access_token(
        cls,
        db: AsyncSession,
        file_id: int,
        user_id: int,
        redis,
        *,
        can_write: bool,
        collabora_url: str,
    ) -> dict:
        entry = await FileService._get_active_file(db, user_id, file_id)
        if not cls._is_office_file(entry):
            raise ThumbnailNotSupported("当前文件类型不支持 Office 在线预览")
        cfg = FileService._cfg(db)
        ttl = int(await cfg.office.access_token_ttl_seconds() or 300)
        now = int(time.time())
        token = secrets.token_urlsafe(32)
        parsed_collabora = urlparse(collabora_url.strip())
        collabora_origin = f"{parsed_collabora.scheme}://{parsed_collabora.netloc}".lower()
        payload = {
            "rid": entry.id,
            "uid": user_id,
            "act": "wopi",
            "can_write": bool(can_write),
            "collabora_origin": collabora_origin,
            "created_at": now,
            "expires_at": now + ttl,
        }
        await redis.setex(f"wopi:tok:{token}", ttl, json.dumps(payload, ensure_ascii=False))
        return {"token": token, "expires_in": ttl, "entry": entry}

    @classmethod
    async def verify_wopi_access_token(
        cls,
        *,
        file_id: int,
        token: str,
        redis,
        request: Request | None = None,
    ) -> dict:
        if not token:
            raise OfficeTokenInvalid("WOPI 访问令牌无效")
        raw = await redis.get(f"wopi:tok:{token}")
        if not raw:
            raise OfficeTokenExpired("WOPI 访问令牌不存在或已过期")
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        try:
            payload = json.loads(raw)
        except Exception as exc:
            raise OfficeTokenInvalid("WOPI 访问令牌解析失败") from exc
        if payload.get("act") != "wopi":
            raise OfficeTokenInvalid("WOPI 访问令牌类型错误")
        if int(payload.get("rid") or 0) != int(file_id):
            raise OfficeTokenInvalid("WOPI 访问令牌与资源不匹配")
        expires_at = int(payload.get("expires_at") or 0)
        if expires_at and int(time.time()) > expires_at:
            raise OfficeTokenExpired("WOPI 访问令牌已过期")
        if request is not None:
            expected_origin = str(payload.get("collabora_origin") or "").strip().lower()
            if expected_origin:
                for header in ("origin", "referer"):
                    raw = (request.headers.get(header) or "").strip()
                    if not raw:
                        continue
                    parsed = urlparse(raw)
                    got_origin = f"{parsed.scheme}://{parsed.netloc}".lower()
                    if got_origin and got_origin != expected_origin:
                        raise OfficeForbidden()
        return payload

    @classmethod
    async def get_wopi_check_file_info(
        cls,
        *,
        db: AsyncSession,
        file_id: int,
        token: str,
        redis,
        request: Request | None = None,
    ) -> dict:
        payload = await cls.verify_wopi_access_token(
            file_id=file_id,
            token=token,
            redis=redis,
            request=request,
        )
        uid = int(payload.get("uid") or 0)
        if uid <= 0:
            raise OfficeTokenInvalid("WOPI 访问令牌无效")
        entry = await FileService._get_active_file(db, uid, file_id)
        can_write = bool(payload.get("can_write"))
        user = await db.get(User, uid)
        user_name = f"user-{uid}"
        avatar_url: str | None = None
        cfg = FileService._cfg(db)
        backend_public_url = (await cfg.office.backend_public_url() or "").strip()
        if user:
            user_name = (user.nickname or user.username or user_name).strip() or user_name
            avatar_path = (user.avatar_path or "").strip()
            if avatar_path:
                relative = ProfileService.avatar_url(avatar_path)
                if backend_public_url:
                    avatar_url = cls._join_base_with_path(backend_public_url, relative)
                elif request is not None:
                    avatar_url = cls._absolute_url_from_path(request, relative)
                else:
                    avatar_url = relative
        return {
            "BaseFileName": entry.name,
            "OwnerId": str(entry.user_id),
            "Size": int(entry.size or 0),
            "UserId": str(uid),
            "UserFriendlyName": user_name,
            "Version": str(entry.etag or entry.updated_at or entry.id),
            "UserCanWrite": can_write,
            "SupportsUpdate": can_write,
            "SupportsLocks": False,
            "SupportsGetLock": False,
            "SupportsExtendedLockLength": False,
            "SupportsRename": False,
            "ReadOnly": not can_write,
            # Collabora 会忽略未知字段，这里以兼容形式提供头像信息。
            "UserExtraInfo": {
                "avatar": avatar_url or "",
                "avatar_url": avatar_url or "",
            },
        }

    @classmethod
    async def get_wopi_file_response(
        cls,
        *,
        db: AsyncSession,
        file_id: int,
        token: str,
        redis,
        request: Request | None = None,
    ) -> FileResponse:
        payload = await cls.verify_wopi_access_token(
            file_id=file_id,
            token=token,
            redis=redis,
            request=request,
        )
        uid = int(payload.get("uid") or 0)
        if uid <= 0:
            raise OfficeTokenInvalid("WOPI 访问令牌无效")
        entry = await FileService._get_active_file(db, uid, file_id)
        if entry.is_dir:
            raise PreviewNotSupported("目录不支持 Office 在线编辑")
        storage = await FileService._get_storage_by_id(db, entry.storage_id)
        backend = get_storage_backend(storage)
        abs_path = backend.resolve_abs_path(entry.storage_path)
        media_type = entry.mime_type or mimetypes.guess_type(entry.name or "")[0] or "application/octet-stream"
        response = FileResponse(path=abs_path, filename=entry.name, media_type=media_type)
        response.headers["X-WOPI-ItemVersion"] = str(entry.etag or "")
        return response

    @classmethod
    async def put_wopi_file_contents(
        cls,
        *,
        db: AsyncSession,
        file_id: int,
        token: str,
        redis,
        content: bytes,
        request: Request | None = None,
    ) -> dict:
        payload = await cls.verify_wopi_access_token(
            file_id=file_id,
            token=token,
            redis=redis,
            request=request,
        )
        uid = int(payload.get("uid") or 0)
        if uid <= 0:
            raise OfficeTokenInvalid("WOPI 访问令牌无效")
        if not bool(payload.get("can_write")):
            raise OfficeForbidden("当前令牌不允许写入")
        entry = await FileService._get_active_file(db, uid, file_id)
        if entry.is_dir:
            raise PreviewNotSupported("目录不支持 Office 在线编辑")
        storage = await FileService._get_storage_by_id(db, entry.storage_id)
        backend = get_storage_backend(storage)
        abs_path = backend.resolve_abs_path(entry.storage_path)
        expected_size = len(content)
        additional = max(0, expected_size - int(entry.size or 0))
        await FileService._ensure_quota_available(db, uid, additional)

        def _sync_write() -> None:
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_bytes(content)

        await asyncio.to_thread(_sync_write)
        size, digest = await backend.hash_file(entry.storage_path)
        entry.size = size
        entry.etag = digest
        entry.content_hash = digest
        if not entry.mime_type:
            entry.mime_type = mimetypes.guess_type(entry.name or "")[0]
        await db.commit()
        await db.refresh(entry)
        await FileService.refresh_used_space(db, uid)
        return {"etag": entry.etag}

    @classmethod
    async def issue_office_url(
        cls,
        request: Request,
        db: AsyncSession,
        file_id: int,
        user_id: int,
        redis,
        lang: str | None = None,
        mode: str | None = None,
    ) -> dict:
        entry = await FileService._get_active_file(db, user_id, file_id)
        if not cls._is_office_file(entry):
            raise ThumbnailNotSupported("当前文件类型不支持 Office 在线预览")

        cfg = FileService._cfg(db)
        if not await cfg.office.enabled():
            raise OfficeUnavailable("Office 在线预览未启用")
        provider = (await cfg.office.provider() or "").strip().lower()
        if provider != "collabora":
            raise OfficeUnavailable("当前 Office 服务提供方不受支持")

        collabora_public_url = (await cfg.office.collabora_public_url() or "").strip()
        collabora_inner_url = (await cfg.office.collabora_url() or "").strip()
        collabora_url = collabora_public_url or collabora_inner_url
        if not collabora_url:
            raise OfficeUnavailable("请先配置 Collabora 服务地址")
        verify_tls = await cfg.office.verify_tls()
        timeout_seconds = int(await cfg.office.request_timeout_seconds() or 15)
        normalized_mode = (mode or "view").strip().lower()
        can_write = normalized_mode in {"edit", "write"}
        token_data = await cls.issue_wopi_access_token(
            db=db,
            file_id=file_id,
            user_id=user_id,
            redis=redis,
            can_write=can_write,
            collabora_url=collabora_url,
        )
        entry = token_data["entry"]
        ext = Path(entry.name or "").suffix.lower().lstrip(".")
        urlsrc_map = await cls._get_collabora_urlsrc_map(
            collabora_url=collabora_url,
            verify_tls=bool(verify_tls),
            timeout_seconds=max(timeout_seconds, 1),
        )
        urlsrc = (urlsrc_map.get(ext) or "").strip()
        if not urlsrc:
            raise BadRequestException(f"Collabora 不支持该扩展名: .{ext}")

        backend_public_url = (await cfg.office.backend_public_url() or "").strip()
        api_prefix = settings.APP_API_PREFIX or "/api/v1"
        wopi_path = f"{api_prefix}/wopi/files/{entry.id}"
        if backend_public_url:
            wopi_src = cls._join_base_with_path(backend_public_url, wopi_path)
        else:
            wopi_src = cls._absolute_url_from_path(request, wopi_path)
        separator = "&" if "?" in urlsrc else "?"
        office_lang = await cls._resolve_office_lang(request, cfg, lang)
        query = urlencode(
            {
                "WOPISrc": wopi_src,
                "access_token": token_data["token"],
                "access_token_ttl": int((int(time.time()) + int(token_data["expires_in"])) * 1000),
                "lang": office_lang,
            }
        )
        launch_url = f"{urlsrc}{separator}{query}"
        return {
            "provider": "collabora",
            "url": launch_url,
            "expires_in": int(token_data.get("expires_in") or 0),
        }

