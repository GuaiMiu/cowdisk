"""
上传会话 GC 脚本
python -m app.scripts.upload_gc --dry-run=1
"""

import argparse
import asyncio

from app.core.database import async_session
from app.modules.disk.services.file import FileService


async def _run(dry_run: bool) -> int:
    async with async_session() as db:
        result = await FileService.gc_uploads(db=db, dry_run=dry_run)
    mode = "DRY-RUN" if dry_run else "EXECUTE"
    print(f"[UPLOAD GC] mode={mode}")
    print(f"scanned={result.get('scanned', 0)}")
    print(f"deleted={result.get('deleted', 0)}")
    print(f"skipped={result.get('skipped', 0)}")
    print(f"locked_stale={result.get('locked_stale', 0)}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="上传会话GC")
    parser.add_argument("--dry-run", type=int, default=1, help="1=只预览,0=执行删除")
    args = parser.parse_args()
    dry_run = bool(args.dry_run)
    raise SystemExit(asyncio.run(_run(dry_run)))


if __name__ == "__main__":
    main()

