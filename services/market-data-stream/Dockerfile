# syntax=docker/dockerfile:1.6
# Market-data stream — keeps a websocket / IBKR feed open and pushes ticks
# downstream. Wave 2 owns the entrypoint module.

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

RUN uv sync --no-dev || uv pip install --system .

COPY contracts ./contracts
COPY config ./config
COPY engine ./engine
COPY services ./services

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "print('ok')" || exit 1

# See services/strategy-engine/Dockerfile for the hyphen-vs-underscore note.
CMD ["python", "-m", "services.market_data_stream"]
