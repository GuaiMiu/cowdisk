from copy import deepcopy
import logging
from pathlib import Path

from app.core.config import settings

ALLOWED_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"}
LOGGER_NAMES = ("uvicorn", "uvicorn.error", "uvicorn.access", "app")


class MaxLevelFilter(logging.Filter):
    def __init__(self, max_level: str | int = "WARNING") -> None:
        super().__init__()
        self.max_level = (
            logging._nameToLevel.get(max_level.upper(), logging.WARNING)
            if isinstance(max_level, str)
            else int(max_level)
        )

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= self.max_level

UVICORN_LOG_CONFIG_TEMPLATE = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(asctime)s - %(levelprefix)s %(message)s",
            "use_colors": None,
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(asctime)s - %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "file_app_info": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/app/logs/app/info.log",
            "formatter": "default",
            "mode": "a",
            "encoding": "utf-8",
            "filters": ["below_error"],
            "maxBytes": 10485760,
            "backupCount": 10,
        },
        "file_app_error": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/app/logs/app/error.log",
            "formatter": "default",
            "mode": "a",
            "encoding": "utf-8",
            "level": "ERROR",
            "maxBytes": 10485760,
            "backupCount": 10,
        },
        "file_uv_server": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/app/logs/uv/server.log",
            "formatter": "default",
            "mode": "a",
            "encoding": "utf-8",
            "maxBytes": 10485760,
            "backupCount": 10,
        },
        "file_uv_access": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/app/logs/uv/access.log",
            "formatter": "access",
            "mode": "a",
            "encoding": "utf-8",
            "maxBytes": 10485760,
            "backupCount": 10,
        },
    },
    "filters": {
        "below_error": {"()": "app.core.logging.MaxLevelFilter", "max_level": "WARNING"}
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["default", "file_uv_server"],
            "level": "DEBUG",
            "propagate": False,
        },
        "uvicorn.error": {"level": "DEBUG"},
        "uvicorn.access": {
            "handlers": ["file_uv_access"],
            "level": "DEBUG",
            "propagate": False,
        },
        "app": {
            "handlers": ["default", "file_app_info", "file_app_error"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}


def normalized_uvicorn_log_level() -> str:
    level = (settings.UVICORN_LOG_LEVEL or "INFO").upper()
    return level if level in ALLOWED_LOG_LEVELS else "INFO"


def _resolve_log_path(base_dir: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (base_dir / path).resolve()


def build_uvicorn_log_config() -> dict:
    log_config = deepcopy(UVICORN_LOG_CONFIG_TEMPLATE)

    backend_root = Path(__file__).resolve().parents[2]
    log_root = _resolve_log_path(backend_root, settings.UVICORN_LOG_DIR)
    app_log_dir = _resolve_log_path(log_root, settings.APP_LOG_SUBDIR)
    uv_log_dir = _resolve_log_path(log_root, settings.UVICORN_LOG_SUBDIR)
    for directory in (log_root, app_log_dir, uv_log_dir):
        directory.mkdir(parents=True, exist_ok=True)

    app_info_log_file = (
        _resolve_log_path(app_log_dir, settings.UVICORN_LOG_FILE)
        if settings.UVICORN_LOG_FILE
        else _resolve_log_path(app_log_dir, settings.UVICORN_APP_LOG_FILE)
    )
    app_error_log_file = _resolve_log_path(app_log_dir, settings.APP_ERROR_LOG_FILE)
    uv_server_log_file = _resolve_log_path(uv_log_dir, settings.UVICORN_SERVER_LOG_FILE)
    uv_access_log_file = _resolve_log_path(uv_log_dir, settings.UVICORN_ACCESS_LOG_FILE)

    max_bytes = int(settings.UVICORN_LOG_MAX_BYTES)
    backup_count = int(settings.UVICORN_LOG_BACKUP_COUNT)
    handlers = log_config["handlers"]
    for handler_name, file_path in (
        ("file_app_info", app_info_log_file),
        ("file_app_error", app_error_log_file),
        ("file_uv_server", uv_server_log_file),
        ("file_uv_access", uv_access_log_file),
    ):
        handler = handlers[handler_name]
        handler["filename"] = str(file_path)
        handler["maxBytes"] = max_bytes
        handler["backupCount"] = backup_count

    log_level = normalized_uvicorn_log_level()
    for logger_name in LOGGER_NAMES:
        log_config["loggers"][logger_name]["level"] = log_level

    return log_config
