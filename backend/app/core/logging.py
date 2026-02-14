from copy import deepcopy
from pathlib import Path

from app.core.config import settings

ALLOWED_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"}
LOGGER_NAMES = ("uvicorn", "uvicorn.error", "uvicorn.access", "app")

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
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "file_app": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/app/logs/app.log",
            "formatter": "default",
            "mode": "a",
            "encoding": "utf-8",
            "maxBytes": 10485760,
            "backupCount": 10,
        },
        "file_access": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/app/logs/access.log",
            "formatter": "access",
            "mode": "a",
            "encoding": "utf-8",
            "maxBytes": 10485760,
            "backupCount": 10,
        },
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["default", "file_app"],
            "level": "DEBUG",
            "propagate": False,
        },
        "uvicorn.error": {"level": "DEBUG"},
        "uvicorn.access": {
            "handlers": ["access", "file_access"],
            "level": "DEBUG",
            "propagate": False,
        },
        "app": {
            "handlers": ["default", "file_app"],
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
    log_dir = _resolve_log_path(backend_root, settings.UVICORN_LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    app_log_file = (
        _resolve_log_path(log_dir, settings.UVICORN_LOG_FILE)
        if settings.UVICORN_LOG_FILE
        else _resolve_log_path(log_dir, settings.UVICORN_APP_LOG_FILE)
    )
    access_log_file = _resolve_log_path(log_dir, settings.UVICORN_ACCESS_LOG_FILE)

    max_bytes = int(settings.UVICORN_LOG_MAX_BYTES)
    backup_count = int(settings.UVICORN_LOG_BACKUP_COUNT)
    handlers = log_config["handlers"]
    for handler_name, file_path in (
        ("file_app", app_log_file),
        ("file_access", access_log_file),
    ):
        handler = handlers[handler_name]
        handler["filename"] = str(file_path)
        handler["maxBytes"] = max_bytes
        handler["backupCount"] = backup_count

    log_level = normalized_uvicorn_log_level()
    for logger_name in LOGGER_NAMES:
        log_config["loggers"][logger_name]["level"] = log_level

    return log_config
