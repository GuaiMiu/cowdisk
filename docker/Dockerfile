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
RUN apk add --no-cache nginx
RUN mkdir -p /app/frontend /app/data /app/log /app/config

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=backend/uv.lock,target=uv.lock \
    --mount=type=bind,source=backend/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

COPY backend/pyproject.toml backend/uv.lock ./
COPY backend/ ./
COPY backend/.env.example /app/config/.env

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

COPY --from=frontend-builder /frontend/dist /app/frontend
COPY docker/nginx/default.conf /etc/nginx/http.d/default.conf
COPY docker/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENV PATH="/app/backend/.venv/bin:$PATH"
ENV PYTHONPATH=/app/backend

RUN mkdir -p /app/log

ENTRYPOINT ["/docker-entrypoint.sh"]
