# syntax=docker/dockerfile:1.6
# Pre-baked CI image: a system-installed .venv with project deps + dev deps.
# Built and pushed by .github/workflows/prewarm-ci-base.yml whenever uv.lock
# changes. ci.yml's python job tries to pull this image and copy the .venv
# out of it before falling back to a cold install.

FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_SYSTEM_PYTHON=1

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --extra dev --no-install-project
