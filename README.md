# Cowdisk

Simple self-hosted disk service with a FastAPI backend and a Vite frontend.

## Requirements

- Python 3.12+ (with `uv`) for backend
- Node.js 20+ for frontend
- Docker (optional)

## Backend (local)

```powershell
cd backend
uv sync
uv run python -m uvicorn app.main:app --reload
```

Server defaults to `http://127.0.0.1:8000`.

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
