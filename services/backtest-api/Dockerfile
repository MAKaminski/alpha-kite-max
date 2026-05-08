# syntax=docker/dockerfile:1.6
# Backtest API — FastAPI sidecar that runs scripts/backtest.run_backtest()
# in response to HTTP POSTs from the web app. Runs alongside strategy_engine
# and market_data_stream on Railway.

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_SYSTEM_PYTHON=1 \
    PYTHONPATH=/app

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential curl \
 && rm -rf /var/lib/apt/lists/*

RUN pip install uv

WORKDIR /app

COPY pyproject.toml README.md ./
COPY uv.loc[k] ./
RUN uv pip install --system .

COPY contracts ./contracts
COPY config ./config
COPY engine ./engine
COPY services ./services
COPY scripts ./scripts
COPY tests/fixtures ./tests/fixtures

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://127.0.0.1:8080/healthz || exit 1

CMD ["python", "-m", "services.backtest_api"]
