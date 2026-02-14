"""
@File: local.py
@Author: GuaiMiu
@Date: 2026/2/7
@Version: 1.0
@Description: 本地存储后端
"""

import mimetypes
import os
import shutil
import time
import zipfile
from datetime import datetime
from hashlib import sha1
from pathlib import Path, PurePosixPath
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.core.database import async_session
from app.core.exception import ServiceException
from app.utils.logger import logger
from app.modules.disk.storage.backends.base import ExtractedItem, StoredFileMeta, StorageBackend
from app.modules.disk.utils.io_pool import run_io
from app.modules.system.service.config import build_runtime_config


async def _run_io(func, *args, **kwargs):
    async with async_session() as session:
        cfg = build_runtime_config(session, request_cache={})
        max_workers = await cfg.performance.io_worker_concurrency()
    max_workers = int(max_workers or 1)
    return await run_io(max_workers, func, *args, **kwargs)


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_path: str):
        normalized = (base_path or "storage").strip()
        if (normalized.startswith('"') and normalized.endswith('"')) or (
            normalized.startswith("'") and normalized.endswith("'")
        ):
            normalized = normalized[1:-1].strip()
        self._base_path = Path(normalized or "storage").resolve()
        self._base_path.mkdir(parents=True, exist_ok=True)
        upload_root = settings.UPLOAD_TMP_ROOT or str(self._base_path / ".uploads")
        self._upload_root = Path(upload_root).resolve()
        self._upload_root.mkdir(parents=True, exist_ok=True)

    def _abs_path(self, storage_path: str) -> Path:
        rel = PurePosixPath(storage_path or "")
        if rel.is_absolute() or ".." in rel.parts:
            raise ServiceException(msg="非法存储路径")
        abs_path = (self._base_path / Path(*rel.parts)).resolve()
        if not abs_path.is_relative_to(self._base_path):
            raise ServiceException(msg="非法存储路径")
        return abs_path

    def resolve_abs_path(self, storage_path: str) -> Path:
        """
        将存储相对路径解析为绝对路径。
        仅在后端内部使用，不暴露给用户。
        会校验路径安全性，防止越权访问。
        不检查文件是否存在，仅返回路径。
        并发：纯计算无共享状态。
        性能：路径解析开销极小。
        错误：非法路径抛出 ServiceException。
        返回：绝对路径 Path。
        """
        return self._abs_path(storage_path)

    def ensure_dir(self, storage_path: str) -> None:
        """
        确保存储路径对应目录存在。
        会创建父目录链，避免上层重复判断。
        仅用于目录创建，不写入文件。
        权限由服务层保证，避免越权。
        并发：多线程重复创建是安全的。
        性能：仅进行 mkdir 操作。
        错误：非法路径会抛出异常。
        返回：None。
        """
        abs_path = self._abs_path(storage_path)
        abs_path.mkdir(parents=True, exist_ok=True)

    async def save_upload(
        self, upload: UploadFile, storage_path: str
    ) -> StoredFileMeta:
        """
        保存上传文件到存储路径。
        使用临时文件写入后原子替换，避免部分写入。
        计算内容哈希与大小用于元数据更新。
        失败时会清理临时文件，避免残留。
        上传流读取为固定块，内存占用稳定。
        并发：同一路径写入依赖上层控制。
        错误：I/O 异常会抛出 ServiceException。
        返回：StoredFileMeta 元数据。
        """
        abs_path = self._abs_path(storage_path)
        temp_path = abs_path.with_name(f".{abs_path.name}.uploading-{uuid4().hex}")

        def _sync_write() -> tuple[int, str]:
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            hasher = sha1()
            size = 0
            with temp_path.open("wb") as handle:
                while True:
                    chunk = upload.file.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
                    hasher.update(chunk)
                    size += len(chunk)
            # 原子替换目标文件，避免写入中间态暴露。
            temp_path.replace(abs_path)
            return size, hasher.hexdigest()

        try:
            size, digest = await _run_io(_sync_write)
        except Exception as exc:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise ServiceException(msg=str(exc)) from exc
        finally:
            await upload.close()

        mime_type = upload.content_type or mimetypes.guess_type(abs_path.name)[0]
        return StoredFileMeta(
            size=size,
            etag=digest,
            content_hash=digest,
            mime_type=mime_type,
        )

    async def move(self, src_storage_path: str, dst_storage_path: str) -> None:
        """
        移动文件或目录到目标存储路径。
        会创建目标父目录，确保路径可用。
        依赖 shutil.move 保持跨卷兼容性。
        权限与合法性由 _abs_path 保障。
        并发：同路径竞争由上层控制。
        性能：取决于文件大小与磁盘。
        错误：I/O 异常会抛出错误。
        返回：None。
        """
        src = self._abs_path(src_storage_path)
        dst = self._abs_path(dst_storage_path)

        def _sync_move():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))

        await _run_io(_sync_move)

    async def copy_file(self, src_storage_path: str, dst_storage_path: str) -> None:
        """
        复制文件到目标存储路径。
        仅用于文件复制，不处理目录树。
        会创建目标父目录，确保路径存在。
        权限由路径解析与上层控制。
        并发：同目标路径需上层避免冲突。
        性能：取决于文件大小与磁盘。
        错误：I/O 异常会抛出错误。
        返回：None。
        """
        src = self._abs_path(src_storage_path)
        dst = self._abs_path(dst_storage_path)

        def _sync_copy():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

        await _run_io(_sync_copy)

    async def delete(self, storage_path: str, is_dir: bool) -> None:
        """
        删除指定存储路径。
        is_dir 控制是否删除目录树。
        仅删除存储范围内的路径。
        权限与安全由 _abs_path 保障。
        并发：删除时可能与写入冲突。
        性能：目录删除成本与规模相关。
        错误：忽略部分 OSError。
        返回：None。
        """
        abs_path = self._abs_path(storage_path)

        def _sync_delete():
            if abs_path.exists():
                if is_dir:
                    shutil.rmtree(abs_path)
                else:
                    abs_path.unlink(missing_ok=True)

        await _run_io(_sync_delete)

    async def delete_abs_path(self, abs_path: Path) -> None:
        """
        删除已解析的绝对路径。
        仅用于内部临时文件清理。
        不再做路径安全校验，调用方需保证。
        is_dir 由路径类型决定。
        并发：删除时可能与写入冲突。
        性能：目录删除成本与规模相关。
        错误：忽略部分 OSError。
        返回：None。
        """
        def _sync_delete():
            if abs_path.exists():
                if abs_path.is_dir():
                    shutil.rmtree(abs_path)
                else:
                    abs_path.unlink(missing_ok=True)

        await _run_io(_sync_delete)

    async def move_abs_path(self, abs_path: Path, dst_storage_path: str) -> None:
        """
        将绝对路径移动到存储路径。
        仅用于内部临时文件迁移。
        目标父目录会自动创建。
        权限由调用方保证，不再校验来源路径。
        并发：目标路径竞争由上层控制。
        性能：取决于文件大小与磁盘。
        错误：I/O 异常会抛出错误。
        返回：None。
        """
        dst = self._abs_path(dst_storage_path)

        def _sync_move():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(abs_path), str(dst))

        await _run_io(_sync_move)

    def _tmp_dir(self, user_id: int) -> Path:
        tmp_dir = self._base_path / ".tmp" / str(user_id)
        tmp_dir.mkdir(parents=True, exist_ok=True)
        return tmp_dir

    def _upload_session_dir(self, user_id: int, upload_id: str) -> Path:
        return self._upload_root / str(user_id) / upload_id

    def _upload_parts_dir(self, user_id: int, upload_id: str) -> Path:
        return self._upload_session_dir(user_id, upload_id) / "parts"

    async def read_text(self, storage_path: str) -> tuple[str, int, datetime]:
        """
        读取文本文件内容。
        以 UTF-8 读取并替换非法字符。
        返回内容、大小与修改时间。
        仅用于文本编辑场景。
        权限与路径安全由 _abs_path 保障。
        并发：只读操作不修改状态。
        性能：读取整文件，适合小文本。
        返回：内容与元数据。
        """
        abs_path = self._abs_path(storage_path)

        def _sync_read() -> tuple[str, int, float]:
            content = abs_path.read_text(encoding="utf-8", errors="replace")
            stat = abs_path.stat()
            return content, stat.st_size, stat.st_mtime

        content, size, mtime = await _run_io(_sync_read)
        return content, size, datetime.fromtimestamp(mtime)

    async def write_text(self, storage_path: str, content: str) -> tuple[int, str]:
        """
        写入文本文件内容。
        以 UTF-8 编码写入。
        返回写入后的大小与内容哈希。
        会创建父目录，避免路径不存在。
        并发：同路径写入可能覆盖。
        性能：整文本写入，适合小文件。
        错误：I/O 异常会抛出错误。
        返回：size 与 digest。
        """
        abs_path = self._abs_path(storage_path)

        def _sync_write() -> tuple[int, str]:
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(content, encoding="utf-8")
            size = abs_path.stat().st_size
            digest = sha1(content.encode("utf-8")).hexdigest()
            return size, digest

        return await _run_io(_sync_write)

    async def hash_file(self, storage_path: str) -> tuple[int, str]:
        """
        计算文件大小与内容哈希。
        以固定块读取，避免大文件占用内存。
        仅用于校验与元数据生成。
        权限与路径安全由 _abs_path 保障。
        并发：只读操作不修改状态。
        性能：读取全文件，耗时与大小相关。
        错误：I/O 异常会抛出错误。
        返回：size 与 digest。
        """
        abs_path = self._abs_path(storage_path)

        def _sync_hash():
            hasher = sha1()
            size = 0
            with abs_path.open("rb") as handle:
                while True:
                    chunk = handle.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    hasher.update(chunk)
            return size, hasher.hexdigest()

        return await _run_io(_sync_hash)

    def ensure_upload_session(self, user_id: int, upload_id: str) -> None:
        """
        初始化上传会话目录与 parts 子目录。
        目录存在即表示会话存在。
        不写入任何 meta.json，状态由目录事实表达。
        权限由调用方保证，不在此校验用户。
        并发：重复调用是安全的。
        性能：仅创建目录，开销极小。
        错误：I/O 异常会抛出错误。
        返回：None。
        """
        parts_dir = self._upload_parts_dir(user_id, upload_id)
        parts_dir.mkdir(parents=True, exist_ok=True)

    def get_upload_session_state(self, user_id: int, upload_id: str) -> dict:
        """
        获取上传会话状态与已上传分片信息。
        通过目录存在性与文件名判断状态。
        .lock 表示 finalize 中，.done 表示完成。
        mtime 用于 TTL 计算与 GC。
        不使用数据库或元数据文件。
        并发：只读操作，不修改状态。
        性能：扫描 parts 目录。
        返回：状态字典。
        """
        session_dir = self._upload_session_dir(user_id, upload_id)
        if not session_dir.exists():
            return {"exists": False}
        parts_dir = session_dir / "parts"
        parts: list[int] = []
        uploaded_bytes = 0
        if parts_dir.exists():
            for entry in parts_dir.iterdir():
                if not entry.is_file():
                    continue
                name = entry.name
                if len(name) != 8 or not name.isdigit():
                    continue
                parts.append(int(name))
                try:
                    uploaded_bytes += entry.stat().st_size
                except OSError:
                    continue
        parts.sort()
        return {
            "exists": True,
            "parts": parts,
            "uploaded_bytes": uploaded_bytes,
            "locked": (session_dir / ".lock").exists(),
            "done": (session_dir / ".done").exists(),
            "mtime": session_dir.stat().st_mtime,
        }

    async def write_upload_part(
        self,
        user_id: int,
        upload_id: str,
        part_number: int,
        upload: UploadFile,
    ) -> int:
        """
        写入指定分片文件。
        使用临时文件写入后原子替换分片文件。
        若分片已存在则校验大小以保证幂等。
        成功后会更新会话目录 mtime。
        并发：不同分片可并行写入。
        错误：大小不一致会抛出冲突错误。
        性能：按块写入，内存占用稳定。
        返回：写入分片大小。
        """
        parts_dir = self._upload_parts_dir(user_id, upload_id)
        parts_dir.mkdir(parents=True, exist_ok=True)
        part_name = f"{part_number:08d}"
        part_path = parts_dir / part_name
        temp_path = parts_dir / f".{part_name}.tmp-{uuid4().hex}"

        def _sync_write() -> int:
            size = 0
            with temp_path.open("wb") as handle:
                while True:
                    data = upload.file.read(1024 * 1024)
                    if not data:
                        break
                    handle.write(data)
                    size += len(data)
            if part_path.exists():
                existing = part_path.stat().st_size
                if existing != size:
                    temp_path.unlink(missing_ok=True)
                    raise ServiceException(msg="分片已存在且大小不一致")
                temp_path.unlink(missing_ok=True)
                return size
            # 原子替换，避免出现半写入的分片文件。
            temp_path.replace(part_path)
            return size

        try:
            size = await _run_io(_sync_write)
        finally:
            session_dir = self._upload_session_dir(user_id, upload_id)
            if session_dir.exists():
                try:
                    os.utime(session_dir, None)
                except OSError:
                    pass
        return size

    async def merge_upload_parts(
        self,
        user_id: int,
        upload_id: str,
        total_parts: int,
        storage_path: str,
    ) -> tuple[int, str]:
        """
        顺序合并分片文件为最终文件。
        按分片序号读取，保证顺序一致。
        使用临时文件写入后原子替换目标文件。
        写入完成后执行 fsync 保证落盘。
        并发：需配合上层锁避免并发合并。
        错误：缺失分片会抛出异常。
        性能：顺序 I/O，内存占用恒定。
        返回：最终文件大小与哈希。
        """
        parts_dir = self._upload_parts_dir(user_id, upload_id)
        abs_path = self._abs_path(storage_path)
        temp_path = abs_path.with_name(f".{abs_path.name}.uploading-{uuid4().hex}")

        def _sync_merge() -> tuple[int, str]:
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            hasher = sha1()
            size = 0
            with temp_path.open("wb") as handle:
                for idx in range(1, total_parts + 1):
                    part = parts_dir / f"{idx:08d}"
                    if not part.exists():
                        raise ServiceException(msg=f"缺少分片 {idx}")
                    with part.open("rb") as src:
                        while True:
                            data = src.read(1024 * 1024)
                            if not data:
                                break
                            handle.write(data)
                            size += len(data)
                            hasher.update(data)
                handle.flush()
                os.fsync(handle.fileno())
            # 原子替换目标文件，保证最终文件一致性。
            temp_path.replace(abs_path)
            return size, hasher.hexdigest()

        return await _run_io(_sync_merge)

    def mark_upload_done(self, user_id: int, upload_id: str) -> None:
        """
        标记上传会话完成并清理目录。
        通过 .done 文件标记完成状态。
        完成后会删除整个会话目录。
        不依赖数据库记录上传状态。
        并发：由上层 finalize 锁保证。
        性能：删除会话目录开销较小。
        错误：忽略删除失败。
        返回：None。
        """
        session_dir = self._upload_session_dir(user_id, upload_id)
        done_path = session_dir / ".done"
        done_path.touch(exist_ok=True)
        shutil.rmtree(session_dir, ignore_errors=True)

    def acquire_upload_lock(self, user_id: int, upload_id: str) -> bool:
        """
        尝试获取上传会话的独占锁。
        使用 O_EXCL 创建 .lock 文件保证互斥。
        若锁已存在则返回 False。
        仅用于 finalize 阶段的互斥控制。
        并发：跨进程/线程均可生效。
        性能：仅创建小文件。
        错误：仅捕获已存在的锁冲突。
        返回：是否获取锁成功。
        """
        lock_path = self._upload_session_dir(user_id, upload_id) / ".lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        try:
            fd = os.open(lock_path, flags)
            os.close(fd)
            return True
        except FileExistsError:
            return False

    def release_upload_lock(self, user_id: int, upload_id: str) -> None:
        """
        释放上传会话独占锁。
        删除 .lock 文件，允许后续 finalize。
        仅在 finalize 结束后调用。
        幂等：锁不存在时直接返回。
        并发：由调用方保证调用时机。
        性能：删除小文件开销极小。
        错误：忽略删除异常。
        返回：None。
        """
        lock_path = self._upload_session_dir(user_id, upload_id) / ".lock"
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            return

    def delete_upload_session(self, user_id: int, upload_id: str) -> None:
        """
        删除上传会话目录及其分片。
        用于取消上传或 GC 清理。
        若目录不存在则忽略。
        不检查 .lock 状态，需由上层控制。
        并发：与 finalize 并行可能冲突。
        性能：删除目录开销与分片数量相关。
        错误：忽略删除异常。
        返回：None。
        """
        session_dir = self._upload_session_dir(user_id, upload_id)
        if session_dir.exists():
            shutil.rmtree(session_dir, ignore_errors=True)

    def gc_upload_sessions(
        self,
        session_ttl: int,
        done_ttl: int,
        dry_run: bool = False,
    ) -> dict:
        """
        清理过期上传会话目录。
        依据目录 mtime 与 TTL 判断是否可删除。
        .lock 表示 finalize 中，优先跳过。
        超时锁会记录日志并强制删除。
        done 会话可在 done_ttl 后清理。
        dry_run 为 True 时仅统计不删除。
        性能：扫描上传根目录所有会话。
        返回：扫描与删除统计数据。
        """
        now = time.time()
        scanned = 0
        deleted = 0
        skipped = 0
        locked_stale = 0
        if not self._upload_root.exists():
            return {
                "scanned": scanned,
                "deleted": deleted,
                "skipped": skipped,
                "locked_stale": locked_stale,
            }
        for user_dir in self._upload_root.iterdir():
            if not user_dir.is_dir():
                continue
            for session_dir in user_dir.iterdir():
                if not session_dir.is_dir():
                    continue
                scanned += 1
                lock_path = session_dir / ".lock"
                done_path = session_dir / ".done"
                mtime = session_dir.stat().st_mtime
                age = now - mtime
                if lock_path.exists():
                    if age > session_ttl * 2:
                        locked_stale += 1
                        logger.warning(
                            "上传会话锁超时，准备清理: %s", str(session_dir)
                        )
                    else:
                        skipped += 1
                        continue
                if done_path.exists():
                    if age <= done_ttl:
                        skipped += 1
                        continue
                else:
                    if age <= session_ttl:
                        skipped += 1
                        continue
                if dry_run:
                    deleted += 1
                    continue
                shutil.rmtree(session_dir, ignore_errors=True)
                deleted += 1
        return {
            "scanned": scanned,
            "deleted": deleted,
            "skipped": skipped,
            "locked_stale": locked_stale,
        }

    async def create_zip(
        self,
        user_id: int,
        root_name: str | None,
        entries: list[tuple[str, str, bool]],
    ) -> Path:
        """
        创建 ZIP 文件并返回其临时路径。
        用于压缩任务输出，非流式下载。
        entries 由存储路径与归档名组成。
        会在用户临时目录下生成 zip 文件。
        并发：不同任务使用不同文件名。
        性能：依赖 zipfile 写入磁盘。
        错误：I/O 异常会抛出错误。
        返回：ZIP 文件绝对路径。
        """
        tmp_dir = self._tmp_dir(user_id)
        zip_label = root_name or "archive"
        zip_path = tmp_dir / f"{zip_label}-{uuid4().hex}.zip"

        def _sync_zip():
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                prefix = root_name or ""
                if prefix:
                    zf.writestr(f"{prefix}/", "")
                for storage_path, arcname, is_dir in entries:
                    arc = f"{prefix}/{arcname}" if prefix else arcname
                    if is_dir:
                        if arc:
                            zf.writestr(arc.rstrip("/") + "/", "")
                        continue
                    abs_path = self._abs_path(storage_path)
                    zf.write(abs_path, arcname=arc)

        await _run_io(_sync_zip)
        return zip_path

    async def extract_zip(
        self, zip_storage_path: str, dest_root_storage_path: str
    ) -> list[ExtractedItem]:
        """
        解压 ZIP 文件到目标目录。
        会检查压缩包路径安全性。
        目标路径若冲突将抛出错误。
        返回包含文件与目录的元信息列表。
        仅支持 ZIP 格式。
        并发：同路径解压需上层控制。
        性能：解压大小决定耗时。
        返回：ExtractedItem 列表。
        """
        zip_abs = self._abs_path(zip_storage_path)
        dest_root = self._abs_path(dest_root_storage_path)
        dest_root.mkdir(parents=True, exist_ok=True)

        def _is_safe(rel: PurePosixPath) -> bool:
            return not rel.is_absolute() and ".." not in rel.parts

        extracted: list[ExtractedItem] = []

        def _sync_extract():
            with zipfile.ZipFile(zip_abs, "r") as zf:
                for info in zf.infolist():
                    rel = PurePosixPath(info.filename)
                    if not _is_safe(rel):
                        raise ServiceException(msg="压缩包包含非法路径")
                    if info.is_dir():
                        target = (dest_root / Path(*rel.parts)).resolve()
                        if target.exists() and not target.is_dir():
                            raise ServiceException(msg="解压目标已存在")
                        target.mkdir(parents=True, exist_ok=True)
                        rel_path = rel.as_posix().rstrip("/")
                        if rel_path:
                            extracted.append(
                                ExtractedItem(
                                    rel_path=rel_path,
                                    is_dir=True,
                                    size=0,
                                    content_hash=None,
                                    mime_type=None,
                                )
                            )
                        continue
                    target = (dest_root / Path(*rel.parts)).resolve()
                    if target.exists():
                        raise ServiceException(msg="解压目标已存在")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(info) as src, target.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
                    size, digest = self._hash_abs_path(target)
                    extracted.append(
                        ExtractedItem(
                            rel_path=rel.as_posix(),
                            is_dir=False,
                            size=size,
                            content_hash=digest,
                            mime_type=mimetypes.guess_type(rel.name)[0],
                        )
                    )

        await _run_io(_sync_extract)
        return extracted

    def _hash_abs_path(self, abs_path: Path) -> tuple[int, str]:
        hasher = sha1()
        size = 0
        with abs_path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                hasher.update(chunk)
        return size, hasher.hexdigest()

    def exists_abs_path(self, abs_path: Path) -> bool:
        """
        判断绝对路径是否存在。
        仅用于内部判断临时文件状态。
        不进行路径安全校验。
        并发：只读操作。
        性能：单次文件系统 stat。
        返回：存在为 True。
        """
        return abs_path.exists()

    def cleanup_empty_parents(self, storage_path: str, stop_storage_path: str) -> None:
        """
        清理指定路径的空父目录。
        仅删除空目录，避免误删仍有内容的目录。
        stop_storage_path 为清理的上限目录（包含）。
        权限与路径安全由 _abs_path 保障。
        并发：若目录被其他操作占用，会跳过。
        性能：自底向上逐层检查。
        返回：None。
        """
        try:
            abs_path = self._abs_path(storage_path)
            stop_abs = self._abs_path(stop_storage_path)
        except Exception:
            return
        current = abs_path.parent
        while True:
            if not current.exists() or not current.is_dir():
                break
            try:
                # 仅在目录为空时删除，避免影响其他文件。
                if any(current.iterdir()):
                    break
                current.rmdir()
            except OSError:
                break
            if current == stop_abs:
                break
            current = current.parent

