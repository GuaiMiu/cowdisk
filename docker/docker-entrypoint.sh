#!/bin/sh
set -e

cd /app/backend
/app/backend/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
exec nginx -g "daemon off;"
