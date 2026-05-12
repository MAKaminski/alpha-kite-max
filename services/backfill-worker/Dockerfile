# syntax=docker/dockerfile:1.6
# Backfill worker — one-shot Railway service that pulls historical bars
# from IBKR + computes SMA/VWAP cross signals, then exits. Mirrors the
# strategy-engine Dockerfile so deps come from the same uv.lock.

FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

COPY --link pyproject.toml uv.lock README.md ./

# Railway's BuildKit fork requires `id=` on every --mount=type=cache. The
# alternative is to thread a service-scoped cache key (like the existing
# strategy-engine Dockerfile does); since this is a one-shot worker that
# builds at most a handful of times we skip the cache entirely — the uv
# install is ~10s on a cold cache, not worth the Railway-specific syntax.
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder /app/.venv /app/.venv

WORKDIR /app
# Drop --link on app-source COPYs: Railway's BuildKit fork has been serving
# stale cached layers even when content changed (PR #45's fix to
# backfill_runner.py was on origin/main but the deployed image kept the
# pre-fix version). Plain COPY rebuilds these layers every time, which is
# cheap (these dirs total <1 MB) and rules out a class of "why is old code
# running" debugging.
COPY contracts ./contracts
COPY config ./config
COPY engine ./engine
COPY services ./services
COPY scripts ./scripts

# No healthcheck — this is a one-shot worker. Railway's restartPolicyType
# is set to NEVER in the service config so a clean exit doesn't trigger a
# redeploy loop.

CMD ["python", "-m", "scripts.backfill_runner"]
