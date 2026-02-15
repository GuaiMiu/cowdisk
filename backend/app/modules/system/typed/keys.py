from __future__ import annotations


class ConfigKey:
    SYSTEM_SITE_NAME = "system.site_name"
    SYSTEM_SITE_DESCRIPTION = "system.site_description"
    SYSTEM_SITE_LOGO_URL = "system.site_logo_url"
    SYSTEM_SITE_FAVICON_URL = "system.site_favicon_url"
    SYSTEM_LOGIN_BACKGROUND_URL = "system.login_background_url"
    SYSTEM_THEME_IMAGE_URL = "system.theme_image_url"
    SYSTEM_DEFAULT_LOCALE = "system.default_locale"
    SYSTEM_DEFAULT_TIMEZONE = "system.default_timezone"
    SYSTEM_ANNOUNCEMENT = "system.announcement"

    AUTH_ALLOW_REGISTER = "auth.allow_register"
    AUTH_DEFAULT_USER_QUOTA_GB = "auth.default_user_quota_gb"

    OFFICE_PROVIDER = "office.provider"
    OFFICE_ENABLED = "office.enabled"
    OFFICE_COLLABORA_URL = "office.collabora_url"
    OFFICE_COLLABORA_PUBLIC_URL = "office.collabora_public_url"
    OFFICE_BACKEND_PUBLIC_URL = "office.backend_public_url"
    OFFICE_OPEN_URL_TEMPLATE = "office.open_url_template"
    OFFICE_ACCESS_TOKEN_TTL_SECONDS = "office.access_token_ttl_seconds"
    OFFICE_JWT_ENABLED = "office.jwt_enabled"
    OFFICE_JWT_SECRET = "office.jwt_secret"
    OFFICE_VERIFY_TLS = "office.verify_tls"
    OFFICE_REQUEST_TIMEOUT_SECONDS = "office.request_timeout_seconds"

    STORAGE_PATH = "storage.path"

    UPLOAD_MAX_SINGLE_FILE_MB = "upload.max_single_file_mb"
    UPLOAD_CHUNK_SIZE_MB = "upload.chunk_size_mb"
    UPLOAD_CHUNK_UPLOAD_THRESHOLD_MB = "upload.chunk_upload_threshold_mb"
    UPLOAD_MAX_PARALLEL_CHUNKS = "upload.max_parallel_chunks"
    UPLOAD_ENABLE_RESUMABLE = "upload.enable_resumable"
    UPLOAD_MAX_CONCURRENCY_PER_USER = "upload.max_concurrency_per_user"
    UPLOAD_CHUNK_RETRY_MAX = "upload.chunk_retry_max"
    UPLOAD_CHUNK_RETRY_BASE_MS = "upload.chunk_retry_base_ms"
    UPLOAD_CHUNK_RETRY_MAX_MS = "upload.chunk_retry_max_ms"

    PREVIEW_MAX_DURATION_SECONDS = "preview.max_duration_seconds"

    DOWNLOAD_TOKEN_TTL_SECONDS = "download.token_ttl_seconds"

    PERFORMANCE_IO_WORKER_CONCURRENCY = "performance.io_worker_concurrency"
    PERFORMANCE_LARGE_FILE_THRESHOLD_MB = "performance.large_file_threshold_mb"

    AUDIT_ENABLE_AUDIT = "audit.enable_audit"
    AUDIT_RETENTION_DAYS = "audit.retention_days"
    AUDIT_LOG_DETAIL_LEVEL = "audit.log_detail_level"
    AUDIT_EXPORT_MAX_ROWS = "audit.export_max_rows"
    AUDIT_OUTBOX_BATCH_SIZE = "audit.outbox_batch_size"
    AUDIT_OUTBOX_LOCK_TIMEOUT_SECONDS = "audit.outbox_lock_timeout_seconds"
    AUDIT_OUTBOX_POLL_INTERVAL_SECONDS = "audit.outbox_poll_interval_seconds"
    AUDIT_OUTBOX_MAX_RETRIES = "audit.outbox_max_retries"
    AUDIT_OUTBOX_RETRY_DELAY_SECONDS = "audit.outbox_retry_delay_seconds"

    DATABASE_TYPE = "database.type"
    DATABASE_HOST = "database.host"
    DATABASE_PORT = "database.port"
    DATABASE_USER = "database.user"
    DATABASE_NAME = "database.name"
    DATABASE_URL = "database.url"

    REDIS_ENABLE = "redis.enable"
    REDIS_HOST = "redis.host"
    REDIS_PORT = "redis.port"
    REDIS_DB = "redis.db"


SECRET_MASK = "******"
