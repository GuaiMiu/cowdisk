"""
@File: config.py
@Author: GuaiMiu
@Date: 2025/3/14 11:09
@Version: 1.0
@Description:
"""

from pathlib import Path

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
    APP_NAME: str | None = None
    APP_DESCRIPTION: str | None = None
    APP_DEBUG: bool | None = None
    APP_HOST: str | None = None
    APP_PORT: int | None = None

    # JWT
    JWT_SECRET_KEY: str | None = None
    JWT_ALGORITHM: str | None = None
    JWT_EXPIRE_MINUTES: int | None = None
    JWT_REDIS_EXPIRE_MINUTES: int | None = None

    ALLOWED_HOSTS: str | None = None
    # 用户相关
    USER_DEFAULT_SPACE: int | None = None

    # Redis
    REDIS_ENABLE: bool | None = None
    REDIS_HOST: str | None = None
    REDIS_PORT: int | None = 6379
    REDIS_DB: int | None = 0
    REDIS_PASSWORD: str | None = None

    # API接口URL
    APP_API_PREFIX: str | None = "/api/v1"

    # 网盘存储目录
    DISK_ROOT: str | None = None


settings = Config()

if __name__ == "__main__":
    settings = Config()
    print(settings.model_dump())
