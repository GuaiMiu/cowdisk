FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.14-alpine
LABEL authors="GuaiMiu"

WORKDIR /app/backend

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PYTHONUNBUFFERED=1
ENV DISK_ROOT=/app/data
ENV UVICORN_LOG_DIR=/app/logs
ENV PATH="/app/backend/.venv/bin:$PATH"
ENV PYTHONPATH=/app/backend

RUN apk add --no-cache nginx
RUN mkdir -p /app/frontend /app/data /app/logs /app/logs/app /app/logs/uv /app/logs/nginx /app/config

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=backend/uv.lock,target=uv.lock \
    --mount=type=bind,source=backend/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

COPY backend/pyproject.toml backend/uv.lock ./
COPY backend/ ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

COPY --from=frontend-builder /frontend/dist /app/frontend
COPY docker/nginx/default.conf /etc/nginx/http.d/default.conf
COPY docker/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1/api/v1/system/setup/status || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
