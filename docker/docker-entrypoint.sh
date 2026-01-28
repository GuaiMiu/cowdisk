#!/bin/sh
set -e

cd /app/backend
/app/backend/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-config /app/backend/uvicorn_config.json &
exec nginx -g "daemon off;"
