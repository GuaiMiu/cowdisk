from __future__ import annotations

SETUP_FIELDS: tuple[str, ...] = (
    "app_name",
    "allow_register",
    "storage_path",
    "database_url",
    "redis_enable",
    "redis_host",
    "redis_port",
    "redis_username",
    "redis_password",
    "redis_db",
    "superuser_name",
    "superuser_password",
    "superuser_mail",
)

SETUP_DEFAULTS: dict[str, object] = {
    "app_name": "CowDisk",
    "allow_register": True,
    "storage_path": "/app/data",
    "database_url": "sqlite+aiosqlite:////app/config/data.db",
    "redis_enable": False,
    "redis_host": "127.0.0.1",
    "redis_port": 6379,
    "redis_username": "",
    "redis_password": "",
    "redis_db": 0,
    "redis_auth_mode": "none",
    "superuser_name": "admin",
    "superuser_password": "",
    "superuser_mail": "admin@example.com",
}


def get_setup_defaults() -> dict[str, object]:
    return dict(SETUP_DEFAULTS)
