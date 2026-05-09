# syntax=docker/dockerfile:1.6
# Market-data stream — keeps an IBKR feed open and pushes ticks downstream.

FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_SYSTEM_PYTHON=1

WORKDIR /app
COPY --link pyproject.toml uv.lock README.md ./

RUN --mount=type=cache,target=/root/.cache/uv \
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

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "print('ok')" || exit 1

CMD ["python", "-m", "services.market_data_stream"]
