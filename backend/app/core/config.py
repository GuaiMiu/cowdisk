"""
@File: config.py
@Author: GuaiMiu
@Date: 2025/3/14 11:09
@Version: 1.0
@Description:
"""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_env_files() -> tuple[str, ...]:
    candidates = [
        "/app/config/.env",
        "/app/backend/.env",
        str(Path.cwd() / ".env"),
        str(Path.cwd() / "backend" / ".env"),
    ]
    return tuple(candidates)


class CustomBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_resolve_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


class Config(CustomBaseSettings):
    APP_VERSION: str = "0.1.0"
    INSTALL_COMPLETED: bool = False

    # 数据库
    DATABASE_HOST: str | None = None
    DATABASE_PORT: int | None = None
    DATABASE_USER: str | None = None
    DATABASE_PASSWORD: str | None = None
    DATABASE_NAME: str | None = None
    DATABASE_URL: str | None = None
    DATABASE_TYPE: str | None = None

    # 超级用户
    SUPERUSER_MAIL: str | None = None
    SUPERUSER_PASSWORD: str | None = None
    SUPERUSER_NAME: str | None = None
    # APP
    APP_NAME: str = "CowDisk"
    APP_DESCRIPTION: str | None = None
    APP_DEBUG: bool = False
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000

    # JWT
    JWT_SECRET_KEY: str | None = None
    JWT_ALGORITHM: str | None = None
    JWT_EXPIRE_MINUTES: int | None = None
    JWT_REDIS_EXPIRE_MINUTES: int | None = None

    ALLOWED_HOSTS: str = "*"
    # 用户相关
    USER_DEFAULT_SPACE: int | None = None

    # Redis
    REDIS_ENABLE: bool = False
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    # API接口URL
    APP_API_PREFIX: str | None = "/api/v1"
    # 对外访问基础 URL（用于下载链接拼接）
    PUBLIC_BASE_URL: str | None = APP_API_PREFIX

    # 网盘存储目录
    DISK_ROOT: str | None = None
    # 单文件最大上传大小(MB)
    UPLOAD_MAX_SIZE: int | None = None
    # 上传优化参数
    DISK_UPLOAD_BUFFER_SIZE: int | None = None
    DISK_UPLOAD_CONCURRENCY: int | None = None
    # 上传会话临时目录(默认: DISK_ROOT/.uploads)
    UPLOAD_TMP_ROOT: str | None = None
    # 上传会话 TTL(秒)
    UPLOAD_SESSION_TTL: int | None = None
    # 上传完成会话 TTL(秒)
    UPLOAD_DONE_TTL: int | None = None
    # 下载 token TTL(秒)
    DOWNLOAD_TOKEN_TTL: int | None = None
    # 预览 token TTL(秒)
    PREVIEW_TOKEN_TTL: int | None = None
    # 预览最大时长(秒)
    PREVIEW_MAX_DURATION: int | None = None

    @field_validator("REDIS_DB", "REDIS_PORT", mode="before")
    @classmethod
    def _normalize_int_fields(cls, value):
        if value == "" or value is None:
            return None
        return value


settings = Config()

def reload_settings() -> Config:
    new_settings = Config()
    fields = getattr(settings, "model_fields", None) or getattr(settings, "__fields__", {})
    for key in fields:
        setattr(settings, key, getattr(new_settings, key))
    return settings

if __name__ == "__main__":
    settings = Config()
    print(settings.model_dump())
