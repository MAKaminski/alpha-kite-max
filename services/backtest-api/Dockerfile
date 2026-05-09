# syntax=docker/dockerfile:1.6
# Backtest API — FastAPI sidecar that runs scripts/backtest.run_backtest()
# in response to HTTP POSTs from the web app.

FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_SYSTEM_PYTHON=1

WORKDIR /app
COPY --link pyproject.toml uv.lock README.md ./

RUN --mount=type=cache,id=s/b705abc8-afbc-4bcd-98df-0b18b859de51-/root/.cache/uv,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

COPY --link --from=builder /app/.venv /app/.venv

WORKDIR /app
COPY --link contracts ./contracts
COPY --link config ./config
COPY --link engine ./engine
COPY --link services ./services
COPY --link scripts ./scripts
COPY --link tests/fixtures ./tests/fixtures

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://127.0.0.1:8080/healthz || exit 1

CMD ["python", "-m", "services.backtest_api"]
