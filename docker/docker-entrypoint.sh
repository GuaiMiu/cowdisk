#!/bin/sh
set -eu

cd /app/backend
/app/backend/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-config /app/backend/uvicorn_config.json &
API_PID=$!

nginx -g "daemon off;" &
NGINX_PID=$!

shutdown() {
  kill -TERM "$API_PID" "$NGINX_PID" 2>/dev/null || true
  wait "$API_PID" 2>/dev/null || true
  wait "$NGINX_PID" 2>/dev/null || true
}

trap 'shutdown; exit 143' INT TERM

while true; do
  if ! kill -0 "$API_PID" 2>/dev/null; then
    shutdown
    exit 1
  fi
  if ! kill -0 "$NGINX_PID" 2>/dev/null; then
    shutdown
    exit 1
  fi
  sleep 2
done
