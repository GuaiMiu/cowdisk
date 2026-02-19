from pathlib import Path

from pydantic import ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_env_files() -> tuple[str, ...]:
    cwd = Path.cwd()
    return (
        "/app/config/.env",
        "/app/backend/.env",
        str(cwd / ".env"),
        str(cwd / "backend" / ".env"),
    )


class CustomBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_resolve_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


class Config(CustomBaseSettings):
    # Install / bootstrap
    APP_VERSION: str = "0.1.0"
    SUPERUSER_MAIL: str | None = None
    SUPERUSER_PASSWORD: str | None = None
    SUPERUSER_NAME: str | None = None

    # App runtime
    APP_NAME: str = "CowDisk"
    APP_DESCRIPTION: str | None = None
    APP_DEBUG: bool = False
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    APP_API_PREFIX: str | None = "/api/v1"
    ALLOWED_HOSTS: str = "*"
    PUBLIC_BASE_URL: str | None = APP_API_PREFIX

    # Auth / token
    JWT_SECRET_KEY: str | None = None
    JWT_ALGORITHM: str | None = None
    JWT_EXPIRE_MINUTES: int = 30
    JWT_REDIS_EXPIRE_MINUTES: int = 30
    JWT_ISSUER: str = "cowdisk"
    JWT_AUDIENCE: str = "cowdisk-web"
    JWT_REFRESH_ROTATE_LIMIT: int = 48
    AUTH_LOGIN_RATE_LIMIT: int = 30
    AUTH_LOGIN_RATE_WINDOW: int = 60
    AUTH_REFRESH_RATE_LIMIT: int = 120
    AUTH_REFRESH_RATE_WINDOW: int = 60
    AUTH_FORCE_LOGOUT_RATE_LIMIT: int = 30
    AUTH_FORCE_LOGOUT_RATE_WINDOW: int = 60

    # Database
    DATABASE_HOST: str | None = None
    DATABASE_PORT: int | None = None
    DATABASE_USER: str | None = None
    DATABASE_PASSWORD: str | None = None
    DATABASE_NAME: str | None = None
    DATABASE_URL: str | None = None
    DATABASE_TYPE: str | None = None

    # Redis
    REDIS_ENABLE: bool = False
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_USERNAME: str | None = None
    REDIS_PASSWORD: str | None = None

    # Disk / upload
    DISK_ROOT: str | None = None
    UPLOAD_MAX_SIZE: int | None = None
    DISK_UPLOAD_BUFFER_SIZE: int | None = None
    DISK_UPLOAD_CONCURRENCY: int | None = None
    UPLOAD_TMP_ROOT: str | None = None
    UPLOAD_SESSION_TTL: int | None = None
    UPLOAD_DONE_TTL: int | None = None
    DOWNLOAD_TOKEN_TTL: int | None = None
    PREVIEW_TOKEN_TTL: int | None = None
    PREVIEW_MAX_DURATION: int | None = None

    # Logging
    UVICORN_LOG_LEVEL: str = "INFO"
    UVICORN_LOG_DIR: str = "logs"
    APP_LOG_SUBDIR: str = "app"
    UVICORN_LOG_SUBDIR: str = "uv"
    UVICORN_APP_LOG_FILE: str = "info.log"
    APP_ERROR_LOG_FILE: str = "error.log"
    UVICORN_SERVER_LOG_FILE: str = "server.log"
    UVICORN_ACCESS_LOG_FILE: str = "access.log"
    # Legacy compatibility: if configured, overrides app info log file path.
    UVICORN_LOG_FILE: str | None = None
    UVICORN_LOG_MAX_BYTES: int = 10 * 1024 * 1024
    UVICORN_LOG_BACKUP_COUNT: int = 10

    @property
    def database_configured(self) -> bool:
        if self.DATABASE_URL:
            return True
        required = (
            self.DATABASE_TYPE,
            self.DATABASE_HOST,
            self.DATABASE_PORT,
            self.DATABASE_USER,
            self.DATABASE_NAME,
        )
        return all(required)

    @field_validator(
        "APP_DESCRIPTION",
        "PUBLIC_BASE_URL",
        "SUPERUSER_MAIL",
        "SUPERUSER_PASSWORD",
        "SUPERUSER_NAME",
        "JWT_SECRET_KEY",
        "JWT_ALGORITHM",
        "DATABASE_HOST",
        "DATABASE_USER",
        "DATABASE_PASSWORD",
        "DATABASE_NAME",
        "DATABASE_URL",
        "DATABASE_TYPE",
        "REDIS_USERNAME",
        "REDIS_PASSWORD",
        "UVICORN_LOG_FILE",
        mode="before",
    )
    @classmethod
    def _normalize_optional_str(cls, value):
        return None if value == "" else value

    _INT_NORMALIZE_FIELDS = (
        "DATABASE_PORT",
        "REDIS_PORT",
        "REDIS_DB",
        "JWT_EXPIRE_MINUTES",
        "JWT_REDIS_EXPIRE_MINUTES",
        "JWT_REFRESH_ROTATE_LIMIT",
        "AUTH_LOGIN_RATE_LIMIT",
        "AUTH_LOGIN_RATE_WINDOW",
        "AUTH_REFRESH_RATE_LIMIT",
        "AUTH_REFRESH_RATE_WINDOW",
        "AUTH_FORCE_LOGOUT_RATE_LIMIT",
        "AUTH_FORCE_LOGOUT_RATE_WINDOW",
        "UPLOAD_MAX_SIZE",
        "DISK_UPLOAD_BUFFER_SIZE",
        "DISK_UPLOAD_CONCURRENCY",
        "UPLOAD_SESSION_TTL",
        "UPLOAD_DONE_TTL",
        "DOWNLOAD_TOKEN_TTL",
        "PREVIEW_TOKEN_TTL",
        "PREVIEW_MAX_DURATION",
    )

    @field_validator(
        *_INT_NORMALIZE_FIELDS,
        mode="before",
    )
    @classmethod
    def _normalize_int_fields(cls, value, info: ValidationInfo):
        if value == "" or value is None:
            default = cls.model_fields[info.field_name].default
            return default if default is not None else None
        return value

    @field_validator("UVICORN_LOG_MAX_BYTES", "UVICORN_LOG_BACKUP_COUNT", mode="after")
    @classmethod
    def _ensure_positive_log_values(cls, value: int):
        return value if value > 0 else 1


settings = Config()


def reload_settings() -> Config:
    new_settings = Config()
    for key in new_settings.model_fields:
        setattr(settings, key, getattr(new_settings, key))
    return settings


if __name__ == "__main__":
    print(Config().model_dump())
