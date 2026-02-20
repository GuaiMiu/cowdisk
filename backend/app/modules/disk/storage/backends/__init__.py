"""
@File: __init__.py
@Author: GuaiMiu
@Date: 2026/2/7
@Version: 1.0
@Description:
"""

from app.core.errors.exceptions import BadRequestException, ServiceUnavailableException
from app.modules.disk.models.storage import Storage
from app.modules.disk.storage.backends.base import StorageBackend
from app.modules.disk.storage.backends.local import LocalStorageBackend

_BACKEND_CACHE: dict[int, StorageBackend] = {}


def get_storage_backend(storage: Storage) -> StorageBackend:
    if storage.id is None:
        raise BadRequestException("存储配置无效")
    cached = _BACKEND_CACHE.get(storage.id)
    if cached:
        return cached
    backend: StorageBackend
    if storage.type == "local":
        backend = LocalStorageBackend(storage.base_path_or_bucket)
    elif storage.type == "minio":
        raise ServiceUnavailableException("MinIO 存储暂未实现")
    else:
        raise BadRequestException("未知存储类型")
    _BACKEND_CACHE[storage.id] = backend
    return backend


def reset_storage_backend_cache(storage_id: int | None = None) -> None:
    """
    清理存储后端缓存。
    storage_id 为空时清空所有缓存。
    """
    if storage_id is None:
        _BACKEND_CACHE.clear()
    else:
        _BACKEND_CACHE.pop(storage_id, None)

