from __future__ import annotations

from typing import Any

from app.modules.system.typed.keys import ConfigKey


class _GroupBase:
    def __init__(self, cfg: "Config") -> None:
        self._cfg = cfg


class SystemTypedConfig(_GroupBase):
    async def site_name(self) -> str:
        return await self._cfg.get_str(ConfigKey.SYSTEM_SITE_NAME)

    async def site_description(self) -> str:
        return await self._cfg.get_str(ConfigKey.SYSTEM_SITE_DESCRIPTION)

    async def site_logo_url(self) -> str:
        return await self._cfg.get_str(ConfigKey.SYSTEM_SITE_LOGO_URL)

    async def site_favicon_url(self) -> str:
        return await self._cfg.get_str(ConfigKey.SYSTEM_SITE_FAVICON_URL)

    async def login_background_url(self) -> str:
        return await self._cfg.get_str(ConfigKey.SYSTEM_LOGIN_BACKGROUND_URL)

    async def theme_image_url(self) -> str:
        return await self._cfg.get_str(ConfigKey.SYSTEM_THEME_IMAGE_URL)

    async def default_locale(self) -> str:
        return await self._cfg.get_str(ConfigKey.SYSTEM_DEFAULT_LOCALE)

    async def default_timezone(self) -> str:
        return await self._cfg.get_str(ConfigKey.SYSTEM_DEFAULT_TIMEZONE)

    async def announcement(self) -> str:
        return await self._cfg.get_str(ConfigKey.SYSTEM_ANNOUNCEMENT)


class AuthTypedConfig(_GroupBase):
    async def allow_register(self) -> bool:
        return await self._cfg.get_bool(ConfigKey.AUTH_ALLOW_REGISTER)

    async def default_user_quota_gb(self) -> int:
        return await self._cfg.get_int(ConfigKey.AUTH_DEFAULT_USER_QUOTA_GB)


class OfficeTypedConfig(_GroupBase):
    async def provider(self) -> str:
        return await self._cfg.get_str(ConfigKey.OFFICE_PROVIDER)

    async def enabled(self) -> bool:
        return await self._cfg.get_bool(ConfigKey.OFFICE_ENABLED)

    async def collabora_url(self) -> str:
        return await self._cfg.get_str(ConfigKey.OFFICE_COLLABORA_URL)

    async def collabora_public_url(self) -> str:
        return await self._cfg.get_str(ConfigKey.OFFICE_COLLABORA_PUBLIC_URL)

    async def backend_public_url(self) -> str:
        return await self._cfg.get_str(ConfigKey.OFFICE_BACKEND_PUBLIC_URL)

    async def open_url_template(self) -> str:
        return await self._cfg.get_str(ConfigKey.OFFICE_OPEN_URL_TEMPLATE)

    async def access_token_ttl_seconds(self) -> int:
        return await self._cfg.get_int(ConfigKey.OFFICE_ACCESS_TOKEN_TTL_SECONDS)

    async def jwt_enabled(self) -> bool:
        return await self._cfg.get_bool(ConfigKey.OFFICE_JWT_ENABLED)

    async def jwt_secret(self) -> str:
        return await self._cfg.get_str(ConfigKey.OFFICE_JWT_SECRET)

    async def verify_tls(self) -> bool:
        return await self._cfg.get_bool(ConfigKey.OFFICE_VERIFY_TLS)

    async def request_timeout_seconds(self) -> int:
        return await self._cfg.get_int(ConfigKey.OFFICE_REQUEST_TIMEOUT_SECONDS)


class StorageTypedConfig(_GroupBase):
    async def path(self) -> str:
        return await self._cfg.get_str(ConfigKey.STORAGE_PATH)


class UploadTypedConfig(_GroupBase):
    async def max_single_file_mb(self) -> int:
        return await self._cfg.get_int(ConfigKey.UPLOAD_MAX_SINGLE_FILE_MB)

    async def chunk_size_mb(self) -> int:
        return await self._cfg.get_int(ConfigKey.UPLOAD_CHUNK_SIZE_MB)

    async def chunk_upload_threshold_mb(self) -> int:
        return await self._cfg.get_int(ConfigKey.UPLOAD_CHUNK_UPLOAD_THRESHOLD_MB)

    async def max_parallel_chunks(self) -> int:
        return await self._cfg.get_int(ConfigKey.UPLOAD_MAX_PARALLEL_CHUNKS)

    async def enable_resumable(self) -> bool:
        return await self._cfg.get_bool(ConfigKey.UPLOAD_ENABLE_RESUMABLE)

    async def max_concurrency_per_user(self) -> int:
        return await self._cfg.get_int(ConfigKey.UPLOAD_MAX_CONCURRENCY_PER_USER)

    async def chunk_retry_max(self) -> int:
        return await self._cfg.get_int(ConfigKey.UPLOAD_CHUNK_RETRY_MAX)

    async def chunk_retry_base_ms(self) -> int:
        return await self._cfg.get_int(ConfigKey.UPLOAD_CHUNK_RETRY_BASE_MS)

    async def chunk_retry_max_ms(self) -> int:
        return await self._cfg.get_int(ConfigKey.UPLOAD_CHUNK_RETRY_MAX_MS)


class PreviewTypedConfig(_GroupBase):
    async def max_duration_seconds(self) -> int:
        return await self._cfg.get_int(ConfigKey.PREVIEW_MAX_DURATION_SECONDS)


class DownloadTypedConfig(_GroupBase):
    async def token_ttl_seconds(self) -> int:
        return await self._cfg.get_int(ConfigKey.DOWNLOAD_TOKEN_TTL_SECONDS)


class PerformanceTypedConfig(_GroupBase):
    async def io_worker_concurrency(self) -> int:
        return await self._cfg.get_int(ConfigKey.PERFORMANCE_IO_WORKER_CONCURRENCY)

    async def large_file_threshold_mb(self) -> int:
        return await self._cfg.get_int(ConfigKey.PERFORMANCE_LARGE_FILE_THRESHOLD_MB)


class AuditTypedConfig(_GroupBase):
    async def enable_audit(self) -> bool:
        return await self._cfg.get_bool(ConfigKey.AUDIT_ENABLE_AUDIT)

    async def retention_days(self) -> int:
        return await self._cfg.get_int(ConfigKey.AUDIT_RETENTION_DAYS)

    async def log_detail_level(self) -> str:
        return await self._cfg.get_str(ConfigKey.AUDIT_LOG_DETAIL_LEVEL)

    async def export_max_rows(self) -> int:
        return await self._cfg.get_int(ConfigKey.AUDIT_EXPORT_MAX_ROWS)

    async def outbox_batch_size(self) -> int:
        return await self._cfg.get_int(ConfigKey.AUDIT_OUTBOX_BATCH_SIZE)

    async def outbox_lock_timeout_seconds(self) -> int:
        return await self._cfg.get_int(ConfigKey.AUDIT_OUTBOX_LOCK_TIMEOUT_SECONDS)

    async def outbox_poll_interval_seconds(self) -> int:
        return await self._cfg.get_int(ConfigKey.AUDIT_OUTBOX_POLL_INTERVAL_SECONDS)

    async def outbox_max_retries(self) -> int:
        return await self._cfg.get_int(ConfigKey.AUDIT_OUTBOX_MAX_RETRIES)

    async def outbox_retry_delay_seconds(self) -> int:
        return await self._cfg.get_int(ConfigKey.AUDIT_OUTBOX_RETRY_DELAY_SECONDS)


class Config:
    def __init__(self, provider: "ConfigProvider") -> None:
        self._provider = provider
        self.system = SystemTypedConfig(self)
        self.auth = AuthTypedConfig(self)
        self.office = OfficeTypedConfig(self)
        self.storage = StorageTypedConfig(self)
        self.upload = UploadTypedConfig(self)
        self.preview = PreviewTypedConfig(self)
        self.download = DownloadTypedConfig(self)
        self.performance = PerformanceTypedConfig(self)
        self.audit = AuditTypedConfig(self)

    async def get_int(self, key: str) -> int:
        value = await self._provider.get_value(key)
        return int(value)

    async def get_bool(self, key: str) -> bool:
        value = await self._provider.get_value(key)
        return bool(value)

    async def get_str(self, key: str) -> str:
        value = await self._provider.get_value(key)
        return str(value)

    async def get_json(self, key: str) -> dict[str, Any] | list[Any]:
        value = await self._provider.get_value(key)
        if isinstance(value, (dict, list)):
            return value
        return {}


class ConfigProvider:
    async def get_value(self, key: str) -> Any:
        raise NotImplementedError
