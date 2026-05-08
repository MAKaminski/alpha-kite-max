# syntax=docker/dockerfile:1.6
# Strategy engine — orchestrator that coordinates signals, risk, execution.
# Wave 2 owns the actual entrypoint module; this image only sets up the runtime.

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_SYSTEM_PYTHON=1 \
    PYTHONPATH=/app

# System deps: minimal set; build-essential only if any wheel falls back to source.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential curl \
 && rm -rf /var/lib/apt/lists/*

# uv is the dependency manager used by this repo.
RUN pip install uv

WORKDIR /app

# Layer-cache deps separately from sources.
COPY pyproject.toml ./
# Optional lockfile; copy only if present (BuildKit treats missing match as no-op via wildcard).
COPY uv.loc[k] ./

# Install runtime deps. Wave 2 may add a uv.lock; until then resolve from pyproject.
RUN uv sync --no-dev || uv pip install --system .

# Copy the project sources used at runtime. We intentionally include the whole
# codebase since the orchestrator imports across packages (contracts, config,
# engine, services).
COPY contracts ./contracts
COPY config ./config
COPY engine ./engine
COPY services ./services

# Placeholder healthcheck — Wave 2 will replace with an HTTP /healthz probe.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "print('ok')" || exit 1

# Module-style entrypoint. The on-disk directory uses a hyphen
# (services/strategy-engine) but Python packages must use underscores; Wave 2
# will add a `services/strategy_engine/__init__.py` shim so this resolves.
CMD ["python", "-m", "services.strategy_engine"]
