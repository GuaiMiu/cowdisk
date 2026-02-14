from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.modules.system.typed.keys import ConfigKey

ConfigValueType = Literal["string", "int", "bool", "json"]


@dataclass(frozen=True)
class ConfigSpec:
    key: str
    group: str
    value_type: ConfigValueType
    default: Any
    description: str
    rules: dict[str, Any] | None = None
    is_secret: bool = False
    editable: bool = True
    env_key: str | None = None
    allow_env_after_install: bool = False


REGISTRY: dict[str, ConfigSpec] = {
    ConfigKey.SYSTEM_SITE_NAME: ConfigSpec(
        key=ConfigKey.SYSTEM_SITE_NAME,
        group="system",
        value_type="string",
        default="笨牛网盘",
        description="站点名称",
        rules={"min_len": 1, "max_len": 30},
    ),
    ConfigKey.SYSTEM_SITE_DESCRIPTION: ConfigSpec(
        key=ConfigKey.SYSTEM_SITE_DESCRIPTION,
        group="system",
        value_type="string",
        default="",
        description="站点描述",
        rules={"max_len": 200},
    ),
    ConfigKey.SYSTEM_SITE_LOGO_URL: ConfigSpec(
        key=ConfigKey.SYSTEM_SITE_LOGO_URL,
        group="system",
        value_type="string",
        default="",
        description="站点 Logo",
        rules={"url_or_empty": True},
    ),
    ConfigKey.SYSTEM_SITE_FAVICON_URL: ConfigSpec(
        key=ConfigKey.SYSTEM_SITE_FAVICON_URL,
        group="system",
        value_type="string",
        default="",
        description="站点 Favicon",
        rules={"url_or_empty": True},
    ),
    ConfigKey.SYSTEM_LOGIN_BACKGROUND_URL: ConfigSpec(
        key=ConfigKey.SYSTEM_LOGIN_BACKGROUND_URL,
        group="system",
        value_type="string",
        default="",
        description="登录页背景图",
        rules={"url_or_empty": True},
    ),
    ConfigKey.SYSTEM_THEME_IMAGE_URL: ConfigSpec(
        key=ConfigKey.SYSTEM_THEME_IMAGE_URL,
        group="system",
        value_type="string",
        default="",
        description="主题图",
        rules={"url_or_empty": True},
    ),
    ConfigKey.SYSTEM_DEFAULT_LOCALE: ConfigSpec(
        key=ConfigKey.SYSTEM_DEFAULT_LOCALE,
        group="system",
        value_type="string",
        default="zh-CN",
        description="默认语言",
        rules={"enum": ["zh-CN", "en-US"]},
    ),
    ConfigKey.SYSTEM_DEFAULT_TIMEZONE: ConfigSpec(
        key=ConfigKey.SYSTEM_DEFAULT_TIMEZONE,
        group="system",
        value_type="string",
        default="Asia/Shanghai",
        description="默认时区",
        rules={"timezone": True},
    ),
    ConfigKey.SYSTEM_ANNOUNCEMENT: ConfigSpec(
        key=ConfigKey.SYSTEM_ANNOUNCEMENT,
        group="system",
        value_type="string",
        default="",
        description="系统公告",
        rules={"max_len": 2000},
    ),
    ConfigKey.AUTH_ALLOW_REGISTER: ConfigSpec(
        key=ConfigKey.AUTH_ALLOW_REGISTER,
        group="auth",
        value_type="bool",
        default=True,
        description="允许注册",
    ),
    ConfigKey.AUTH_DEFAULT_USER_QUOTA_GB: ConfigSpec(
        key=ConfigKey.AUTH_DEFAULT_USER_QUOTA_GB,
        group="auth",
        value_type="int",
        default=10,
        description="新用户默认配额(GB)",
        rules={"min": 1, "max": 10240},
    ),
    ConfigKey.STORAGE_PATH: ConfigSpec(
        key=ConfigKey.STORAGE_PATH,
        group="storage",
        value_type="string",
        default="storage",
        description="本地存储路径",
        rules={"min_len": 1, "max_len": 300},
        env_key="DISK_ROOT",
    ),
    ConfigKey.UPLOAD_MAX_SINGLE_FILE_MB: ConfigSpec(
        key=ConfigKey.UPLOAD_MAX_SINGLE_FILE_MB,
        group="upload",
        value_type="int",
        default=1024,
        description="单文件最大上传大小(MB)",
        rules={"min": 1, "max": 102400},
        env_key="UPLOAD_MAX_SIZE",
    ),
    ConfigKey.UPLOAD_CHUNK_SIZE_MB: ConfigSpec(
        key=ConfigKey.UPLOAD_CHUNK_SIZE_MB,
        group="upload",
        value_type="int",
        default=8,
        description="分片大小(MB)",
        rules={"min": 1, "max": 256},
    ),
    ConfigKey.UPLOAD_CHUNK_UPLOAD_THRESHOLD_MB: ConfigSpec(
        key=ConfigKey.UPLOAD_CHUNK_UPLOAD_THRESHOLD_MB,
        group="upload",
        value_type="int",
        default=10,
        description="启用分片上传阈值(MB)",
        rules={"min": 1, "max": 102400},
    ),
    ConfigKey.UPLOAD_MAX_PARALLEL_CHUNKS: ConfigSpec(
        key=ConfigKey.UPLOAD_MAX_PARALLEL_CHUNKS,
        group="upload",
        value_type="int",
        default=4,
        description="分片并发数",
        rules={"min": 1, "max": 32},
    ),
    ConfigKey.UPLOAD_ENABLE_RESUMABLE: ConfigSpec(
        key=ConfigKey.UPLOAD_ENABLE_RESUMABLE,
        group="upload",
        value_type="bool",
        default=True,
        description="启用断点续传",
    ),
    ConfigKey.UPLOAD_MAX_CONCURRENCY_PER_USER: ConfigSpec(
        key=ConfigKey.UPLOAD_MAX_CONCURRENCY_PER_USER,
        group="upload",
        value_type="int",
        default=2,
        description="单用户上传并发",
        rules={"min": 1, "max": 20},
    ),
    ConfigKey.UPLOAD_CHUNK_RETRY_MAX: ConfigSpec(
        key=ConfigKey.UPLOAD_CHUNK_RETRY_MAX,
        group="upload",
        value_type="int",
        default=3,
        description="分片重试次数",
        rules={"min": 0, "max": 20},
    ),
    ConfigKey.UPLOAD_CHUNK_RETRY_BASE_MS: ConfigSpec(
        key=ConfigKey.UPLOAD_CHUNK_RETRY_BASE_MS,
        group="upload",
        value_type="int",
        default=600,
        description="分片重试基础退避(ms)",
        rules={"min": 100, "max": 10000},
    ),
    ConfigKey.UPLOAD_CHUNK_RETRY_MAX_MS: ConfigSpec(
        key=ConfigKey.UPLOAD_CHUNK_RETRY_MAX_MS,
        group="upload",
        value_type="int",
        default=6000,
        description="分片重试最大退避(ms)",
        rules={"min": 100, "max": 60000},
    ),
    ConfigKey.PREVIEW_MAX_DURATION_SECONDS: ConfigSpec(
        key=ConfigKey.PREVIEW_MAX_DURATION_SECONDS,
        group="preview",
        value_type="int",
        default=10800,
        description="预览最大时长(秒)",
        rules={"min": 60, "max": 86400},
        env_key="PREVIEW_MAX_DURATION",
    ),
    ConfigKey.DOWNLOAD_TOKEN_TTL_SECONDS: ConfigSpec(
        key=ConfigKey.DOWNLOAD_TOKEN_TTL_SECONDS,
        group="download",
        value_type="int",
        default=7200,
        description="下载 token 过期时间(秒)",
        rules={"min": 60, "max": 86400},
        env_key="DOWNLOAD_TOKEN_TTL",
    ),
    ConfigKey.PERFORMANCE_IO_WORKER_CONCURRENCY: ConfigSpec(
        key=ConfigKey.PERFORMANCE_IO_WORKER_CONCURRENCY,
        group="performance",
        value_type="int",
        default=8,
        description="I/O 线程并发",
        rules={"min": 1, "max": 64},
    ),
    ConfigKey.PERFORMANCE_LARGE_FILE_THRESHOLD_MB: ConfigSpec(
        key=ConfigKey.PERFORMANCE_LARGE_FILE_THRESHOLD_MB,
        group="performance",
        value_type="int",
        default=256,
        description="大文件阈值(MB)",
        rules={"min": 1, "max": 102400},
    ),
    ConfigKey.AUDIT_ENABLE_AUDIT: ConfigSpec(
        key=ConfigKey.AUDIT_ENABLE_AUDIT,
        group="audit",
        value_type="bool",
        default=True,
        description="启用审计日志",
    ),
    ConfigKey.AUDIT_RETENTION_DAYS: ConfigSpec(
        key=ConfigKey.AUDIT_RETENTION_DAYS,
        group="audit",
        value_type="int",
        default=90,
        description="日志保留天数",
        rules={"min": 7, "max": 3650},
    ),
    ConfigKey.AUDIT_LOG_DETAIL_LEVEL: ConfigSpec(
        key=ConfigKey.AUDIT_LOG_DETAIL_LEVEL,
        group="audit",
        value_type="string",
        default="full",
        description="日志详情级别",
        rules={"enum": ["basic", "full"]},
    ),
    ConfigKey.AUDIT_EXPORT_MAX_ROWS: ConfigSpec(
        key=ConfigKey.AUDIT_EXPORT_MAX_ROWS,
        group="audit",
        value_type="int",
        default=50000,
        description="导出最大行数",
        rules={"min": 1000, "max": 200000},
    ),
    ConfigKey.AUDIT_OUTBOX_BATCH_SIZE: ConfigSpec(
        key=ConfigKey.AUDIT_OUTBOX_BATCH_SIZE,
        group="audit",
        value_type="int",
        default=100,
        description="审计 outbox 批量处理大小",
        rules={"min": 1, "max": 1000},
    ),
    ConfigKey.AUDIT_OUTBOX_LOCK_TIMEOUT_SECONDS: ConfigSpec(
        key=ConfigKey.AUDIT_OUTBOX_LOCK_TIMEOUT_SECONDS,
        group="audit",
        value_type="int",
        default=30,
        description="审计 outbox 锁超时(秒)",
        rules={"min": 5, "max": 3600},
    ),
    ConfigKey.AUDIT_OUTBOX_POLL_INTERVAL_SECONDS: ConfigSpec(
        key=ConfigKey.AUDIT_OUTBOX_POLL_INTERVAL_SECONDS,
        group="audit",
        value_type="int",
        default=2,
        description="审计 outbox 轮询间隔(秒)",
        rules={"min": 1, "max": 60},
    ),
    ConfigKey.AUDIT_OUTBOX_MAX_RETRIES: ConfigSpec(
        key=ConfigKey.AUDIT_OUTBOX_MAX_RETRIES,
        group="audit",
        value_type="int",
        default=10,
        description="审计 outbox 最大重试次数",
        rules={"min": 1, "max": 100},
    ),
    ConfigKey.AUDIT_OUTBOX_RETRY_DELAY_SECONDS: ConfigSpec(
        key=ConfigKey.AUDIT_OUTBOX_RETRY_DELAY_SECONDS,
        group="audit",
        value_type="int",
        default=5,
        description="审计 outbox 重试退避间隔(秒)",
        rules={"min": 1, "max": 600},
    ),
    ConfigKey.DATABASE_TYPE: ConfigSpec(
        key=ConfigKey.DATABASE_TYPE,
        group="infra",
        value_type="string",
        default="sqlite",
        description="数据库类型",
        editable=False,
        env_key="DATABASE_TYPE",
        allow_env_after_install=True,
    ),
    ConfigKey.DATABASE_HOST: ConfigSpec(
        key=ConfigKey.DATABASE_HOST,
        group="infra",
        value_type="string",
        default="127.0.0.1",
        description="数据库地址",
        editable=False,
        env_key="DATABASE_HOST",
        allow_env_after_install=True,
    ),
    ConfigKey.DATABASE_PORT: ConfigSpec(
        key=ConfigKey.DATABASE_PORT,
        group="infra",
        value_type="int",
        default=3306,
        description="数据库端口",
        editable=False,
        env_key="DATABASE_PORT",
        allow_env_after_install=True,
    ),
    ConfigKey.DATABASE_USER: ConfigSpec(
        key=ConfigKey.DATABASE_USER,
        group="infra",
        value_type="string",
        default="",
        description="数据库用户名",
        editable=False,
        env_key="DATABASE_USER",
        allow_env_after_install=True,
    ),
    ConfigKey.DATABASE_NAME: ConfigSpec(
        key=ConfigKey.DATABASE_NAME,
        group="infra",
        value_type="string",
        default="",
        description="数据库名称",
        editable=False,
        env_key="DATABASE_NAME",
        allow_env_after_install=True,
    ),
    ConfigKey.DATABASE_URL: ConfigSpec(
        key=ConfigKey.DATABASE_URL,
        group="infra",
        value_type="string",
        default="sqlite+aiosqlite:///./data.db",
        description="数据库连接 URL",
        editable=False,
        env_key="DATABASE_URL",
        allow_env_after_install=True,
    ),
    ConfigKey.REDIS_ENABLE: ConfigSpec(
        key=ConfigKey.REDIS_ENABLE,
        group="infra",
        value_type="bool",
        default=False,
        description="是否启用 Redis",
        editable=False,
        env_key="REDIS_ENABLE",
        allow_env_after_install=True,
    ),
    ConfigKey.REDIS_HOST: ConfigSpec(
        key=ConfigKey.REDIS_HOST,
        group="infra",
        value_type="string",
        default="127.0.0.1",
        description="Redis 地址",
        editable=False,
        env_key="REDIS_HOST",
        allow_env_after_install=True,
    ),
    ConfigKey.REDIS_PORT: ConfigSpec(
        key=ConfigKey.REDIS_PORT,
        group="infra",
        value_type="int",
        default=6379,
        description="Redis 端口",
        editable=False,
        env_key="REDIS_PORT",
        allow_env_after_install=True,
    ),
    ConfigKey.REDIS_DB: ConfigSpec(
        key=ConfigKey.REDIS_DB,
        group="infra",
        value_type="int",
        default=0,
        description="Redis DB",
        editable=False,
        env_key="REDIS_DB",
        allow_env_after_install=True,
    ),
}

GROUPS: tuple[str, ...] = tuple(sorted({spec.group for spec in REGISTRY.values()}))

STATIC_ENV_KEYS: set[str] = {
    key for key, spec in REGISTRY.items() if spec.allow_env_after_install
}


def get_spec(key: str) -> ConfigSpec:
    spec = REGISTRY.get(key)
    if spec is None:
        raise KeyError(f"unknown config key: {key}")
    return spec


def get_default(key: str, fallback: Any = None) -> Any:
    spec = REGISTRY.get(key)
    return spec.default if spec is not None else fallback
