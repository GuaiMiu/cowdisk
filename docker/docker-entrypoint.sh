#!/bin/sh
set -eu

log() {
  # UTC timestamp keeps container logs sortable across hosts.
  printf '%s [entrypoint] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*"
}

mkdir -p /app/logs/app /app/logs/uv /app/logs/nginx

cd /app/backend
log "starting api process"
python -m app.main &
API_PID=$!
log "api started pid=$API_PID"

log "starting nginx process"
nginx -g "daemon off;" &
NGINX_PID=$!
log "nginx started pid=$NGINX_PID"

shutdown() {
  log "shutting down api pid=$API_PID and nginx pid=$NGINX_PID"
  kill -TERM "$API_PID" "$NGINX_PID" 2>/dev/null || true
  wait "$API_PID" 2>/dev/null || true
  wait "$NGINX_PID" 2>/dev/null || true
  log "shutdown complete"
}

trap 'shutdown; exit 143' INT TERM

while true; do
  if ! kill -0 "$API_PID" 2>/dev/null; then
    API_EXIT=0
    wait "$API_PID" || API_EXIT=$?
    log "api exited unexpectedly code=$API_EXIT"
    shutdown
    exit 1
  fi
  if ! kill -0 "$NGINX_PID" 2>/dev/null; then
    NGINX_EXIT=0
    wait "$NGINX_PID" || NGINX_EXIT=$?
    log "nginx exited unexpectedly code=$NGINX_EXIT"
    shutdown
    exit 1
  fi
  sleep 2
done
