# Cowdisk

Simple self-hosted disk service with a FastAPI backend and a Vite frontend.

## Requirements

- Python 3.12+ (with `uv`) for backend
- Node.js 20+ for frontend
- Docker (optional)

## Backend (local)

Initial setup does not require a database connection. Configure your database
settings in `backend/.env` before switching away from the default SQLite setup.

```powershell
cd backend
uv sync
uv run python -m app.main
```

Server defaults to `http://127.0.0.1:8000`.
日志配置可通过 `backend/.env` 调整：`UVICORN_LOG_LEVEL`、`UVICORN_LOG_DIR`、`UVICORN_APP_LOG_FILE`、`UVICORN_ACCESS_LOG_FILE`、`UVICORN_LOG_MAX_BYTES`、`UVICORN_LOG_BACKUP_COUNT`（默认目录 `logs`；Docker 中为 `/app/logs`）。

## Configuration Center

The backend exposes admin configuration modules under `/api/v1/admin/system/config*`:

- Groups list: `/api/v1/admin/system/config/groups`
- Group detail: `/api/v1/admin/system/config?group=system`
- Batch update: `/api/v1/admin/system/config/batch`

Key defaults (registry):

- System
  - `system.site_name`: "笨牛网盘"
  - `system.site_logo_url`: ""
  - `system.default_locale`: "zh-CN"
  - `system.default_timezone`: "Asia/Shanghai"
  - `system.allow_register`: true
  - `system.default_user_quota_gb`: 10
  - `system.max_single_file_mb`: 1024
  - `system.announcement`: ""
- Performance (merged into system config UI tab)
  - `performance.chunk_size_mb`: 8
  - `performance.max_parallel_chunks`: 4
  - `performance.enable_resumable`: true
  - `performance.enable_hash_verify`: true
  - `performance.enable_instant_upload`: true
  - `performance.max_upload_concurrency_per_user`: 2
  - `performance.io_worker_concurrency`: 8
  - `performance.large_file_threshold_mb`: 256
- Audit
  - `audit.enable_audit`: true
  - `audit.retention_days`: 90
  - `audit.log_detail_level`: "basic"
  - `audit.export_max_rows`: 50000

Upload init responses include `upload_config` for the frontend.

Audit management endpoints:

- `/api/v1/admin/audit/logs`
- `/api/v1/admin/audit/logs/export`
- `/api/v1/admin/audit/cleanup`

## Migrations

Alembic config lives in `backend/alembic.ini` and `backend/migrations/`.

```powershell
cd backend
uv run alembic upgrade head
```

## Upload GC (cleanup)

Dry-run (preview only):

```powershell
python -m app.scripts.upload_gc --dry-run=1
```

Execute delete:

```powershell
python -m app.scripts.upload_gc --dry-run=0
```

Example output:

```text
[UPLOAD GC] mode=DRY-RUN
scanned=12
deleted=3
skipped=9
locked_stale=1
```

## Frontend (local)

```powershell
cd frontend
npm ci
npm run dev
```

Vite defaults to `http://127.0.0.1:5173`.

## Docker (build/run)

```powershell
docker build -f docker/Dockerfile -t cowdisk .
docker run --rm -p 80:80 cowdisk
```

Nginx serves the frontend and proxies `/api/` to the backend inside the same container.
