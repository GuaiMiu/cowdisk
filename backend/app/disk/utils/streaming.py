"""
@File: streaming.py
@Author: GuaiMiu
@Date: 2026/1/25
@Version: 1.0
@Description: File streaming helpers for inline/download responses.
"""

import re
from email.utils import formatdate
from pathlib import Path
from urllib.parse import quote

from fastapi import Request
from starlette.background import BackgroundTask
from starlette.responses import FileResponse, Response, StreamingResponse


def build_file_response(
    request: Request,
    file_path: Path,
    filename: str,
    background: BackgroundTask | None,
) -> Response:
    range_header = request.headers.get("range")
    stat = file_path.stat()
    size = stat.st_size
    mtime = int(stat.st_mtime)
    last_modified = formatdate(mtime, usegmt=True)
    etag = f'W/"{size}-{mtime}"'
    if not range_header:
        return FileResponse(
            file_path,
            filename=filename,
            background=background,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(size),
                "Content-Encoding": "identity",
                "ETag": etag,
                "Last-Modified": last_modified,
            },
        )

    match = re.match(r"bytes=(\d*)-(\d*)", range_header)
    if not match:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})
    start_str, end_str = match.groups()
    start = int(start_str) if start_str else 0
    end = int(end_str) if end_str else size - 1
    if start >= size or end < start:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})

    response = StreamingResponse(
        iter_file_range(file_path, start, end),
        status_code=206,
        headers={
            "Content-Range": f"bytes {start}-{end}/{size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "Content-Disposition": content_disposition(filename, inline=False),
            "Content-Encoding": "identity",
            "ETag": etag,
            "Last-Modified": last_modified,
        },
        media_type="application/octet-stream",
        background=background,
    )
    return response


def build_inline_response(
    request: Request,
    file_path: Path,
    filename: str,
    media_type: str,
    background: BackgroundTask | None,
) -> Response:
    range_header = request.headers.get("range")
    stat = file_path.stat()
    size = stat.st_size
    mtime = int(stat.st_mtime)
    last_modified = formatdate(mtime, usegmt=True)
    etag = f'W/"{size}-{mtime}"'
    if request.method == "HEAD":
        if range_header:
            match = re.match(r"bytes=(\d*)-(\d*)", range_header)
            if not match:
                return Response(
                    status_code=416, headers={"Content-Range": f"bytes */{size}"}
                )
            start_str, end_str = match.groups()
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else size - 1
            if start >= size or end < start:
                return Response(
                    status_code=416, headers={"Content-Range": f"bytes */{size}"}
                )
            return Response(
                status_code=206,
                headers={
                    "Content-Range": f"bytes {start}-{end}/{size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(end - start + 1),
                    "Content-Disposition": content_disposition(filename, inline=True),
                    "Content-Encoding": "identity",
                    "ETag": etag,
                    "Last-Modified": last_modified,
                    "Content-Type": media_type,
                },
            )
        return Response(
            status_code=200,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(size),
                "Content-Encoding": "identity",
                "ETag": etag,
                "Last-Modified": last_modified,
                "Content-Disposition": content_disposition(filename, inline=True),
                "Content-Type": media_type,
            },
        )

    if not range_header:
        if media_type.startswith(("video/", "audio/")) and size > 0:
            end = min(size - 1, 1024 * 1024 - 1)
            range_header = f"bytes=0-{end}"
        else:
            return FileResponse(
                file_path,
                filename=filename,
                background=background,
                media_type=media_type,
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(size),
                    "Content-Encoding": "identity",
                    "ETag": etag,
                    "Last-Modified": last_modified,
                    "Content-Disposition": content_disposition(filename, inline=True),
                },
            )

    match = re.match(r"bytes=(\d*)-(\d*)", range_header)
    if not match:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})
    start_str, end_str = match.groups()
    start = int(start_str) if start_str else 0
    end = int(end_str) if end_str else size - 1
    if start >= size or end < start:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})

    response = StreamingResponse(
        iter_file_range(file_path, start, end),
        status_code=206,
        headers={
            "Content-Range": f"bytes {start}-{end}/{size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "Content-Disposition": content_disposition(filename, inline=True),
            "Content-Encoding": "identity",
            "ETag": etag,
            "Last-Modified": last_modified,
        },
        media_type=media_type,
        background=background,
    )
    return response


def content_disposition(filename: str, inline: bool) -> str:
    disposition = "inline" if inline else "attachment"
    try:
        filename.encode("latin-1")
        return f'{disposition}; filename="{filename}"'
    except UnicodeEncodeError:
        fallback = "".join(
            char if ord(char) < 128 and char not in {'"', "\\"} else "_"
            for char in filename
        )
        quoted = quote(filename)
        return f'{disposition}; filename="{fallback}"; filename*=UTF-8\'\'{quoted}'


def iter_file_range(file_path: Path, start: int, end: int, chunk_size: int = 8192):
    with file_path.open("rb") as handle:
        handle.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            read_size = min(chunk_size, remaining)
            data = handle.read(read_size)
            if not data:
                break
            remaining -= len(data)
            yield data
