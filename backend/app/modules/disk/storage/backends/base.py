"""
@File: base.py
@Author: GuaiMiu
@Date: 2026/2/7
@Version: 1.0
@Description:
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile


@dataclass
class StoredFileMeta:
    size: int
    etag: str
    content_hash: str | None
    mime_type: str | None


@dataclass
class ExtractedItem:
    rel_path: str
    is_dir: bool
    size: int
    content_hash: str | None
    mime_type: str | None


class StorageBackend:
    def ensure_dir(self, storage_path: str) -> None:
        raise NotImplementedError

    async def save_upload(
        self, upload: UploadFile, storage_path: str
    ) -> StoredFileMeta:
        raise NotImplementedError

    async def move(self, src_storage_path: str, dst_storage_path: str) -> None:
        raise NotImplementedError

    async def copy_file(
        self, src_storage_path: str, dst_storage_path: str
    ) -> None:
        raise NotImplementedError

    async def delete(self, storage_path: str, is_dir: bool) -> None:
        raise NotImplementedError

    def resolve_abs_path(self, storage_path: str) -> Path:
        raise NotImplementedError

    async def read_text(self, storage_path: str) -> tuple[str, int, datetime]:
        raise NotImplementedError

    async def write_text(self, storage_path: str, content: str) -> tuple[int, str]:
        raise NotImplementedError

    async def hash_file(self, storage_path: str) -> tuple[int, str]:
        raise NotImplementedError

    def ensure_upload_session(self, user_id: int, upload_id: str) -> None:
        raise NotImplementedError

    def get_upload_session_state(self, user_id: int, upload_id: str) -> dict:
        raise NotImplementedError

    async def write_upload_part(
        self,
        user_id: int,
        upload_id: str,
        part_number: int,
        upload: UploadFile,
    ) -> int:
        raise NotImplementedError

    async def merge_upload_parts(
        self,
        user_id: int,
        upload_id: str,
        total_parts: int,
        storage_path: str,
    ) -> tuple[int, str]:
        raise NotImplementedError

    def mark_upload_done(self, user_id: int, upload_id: str) -> None:
        raise NotImplementedError

    def acquire_upload_lock(self, user_id: int, upload_id: str) -> bool:
        raise NotImplementedError

    def release_upload_lock(self, user_id: int, upload_id: str) -> None:
        raise NotImplementedError

    def delete_upload_session(self, user_id: int, upload_id: str) -> None:
        raise NotImplementedError

    def gc_upload_sessions(
        self,
        session_ttl: int,
        done_ttl: int,
        dry_run: bool = False,
    ) -> dict:
        raise NotImplementedError

    async def create_zip(
        self,
        user_id: int,
        root_name: str | None,
        entries: list[tuple[str, str, bool]],
    ) -> Path:
        raise NotImplementedError

    async def extract_zip(
        self, zip_storage_path: str, dest_root_storage_path: str
    ) -> list[ExtractedItem]:
        raise NotImplementedError

    async def delete_abs_path(self, abs_path: Path) -> None:
        raise NotImplementedError

    async def move_abs_path(self, abs_path: Path, dst_storage_path: str) -> None:
        raise NotImplementedError

    def exists_abs_path(self, abs_path: Path) -> bool:
        raise NotImplementedError
