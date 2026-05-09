# Architecture

This document covers two layers:

1. **Runtime** — how the trading engine, data feeds, risk pipeline, persistence, and dashboard fit together.
2. **Build & deploy** — how source becomes containers and lands on Railway/Vercel, and the cache strategy that keeps it fast.

For product framing and the phase plan, see [`README.md`](README.md). For day-to-day commands and conventions, see [`CLAUDE.md`](CLAUDE.md).

---

## 1. Runtime architecture

### Layered dependencies

```
contracts/  ←  config/  ←  engine/  ←  services/  ←  scripts/, apps/web/
```

- **`contracts/`** — frozen `pydantic.BaseModel` data classes (`OrderIntent`, `Bar`, `Quote`, `OptionQuote`, `Signal`) and `Protocol`s (`Strategy`, `BrokerGateway`, `MarketDataFeed`, `RiskGuard`). Every other layer imports *from* contracts; nothing modifies them. Treat changes here as breaking-API changes.
- **`engine/`** — implementations of the contracts. Pure-function indicators (`engine/indicators/`), data feeds (`engine/data_feeds/`, with a `factory.py` selecting between `yfinance` / `ibkr_delayed` / `replay` / `synthetic_options` / `ibkr_live`), strategies (`engine/strategies/`, one file per strategy), brokers (`engine/broker/`), and risk guards (`engine/risk/`).
- **`services/`** — long-running processes that wire engine pieces together: `services/strategy_engine/` (orchestrator), `services/market_data_stream/` (always-on tick capture), `services/backtest_api/` (FastAPI sidecar), `services/persistence/` (Supabase + in-memory backends).
- **`apps/web/`** — Next.js 15 App Router dashboard. Server components query Supabase directly.

### The orchestrator (`services/strategy_engine/main.py`)

Single linchpin file that combines feed → strategy → risk → broker → persistence. Important behaviors:

- **Strategy `kind` selects the event loop.** Bar strategies drive `feed.stream_equity_bars` → `on_bar`; tick strategies drive `feed.stream_equity_quotes` → `on_tick`.
- **Strategies emit `OrderIntent`; the orchestrator runs `RiskPipeline.evaluate()`; only survivors reach `broker.place_order`.** Strategies must not call brokers directly.
- **`runtime_settings.dry_run_override` overrides config.** A heartbeat task polls Supabase every ~60 s for an override row (migration `0004`); when present it flips `effective_dry_run` and mutates `broker.dry_run` in place. Lets the dashboard's `/live-enable` flow toggle dry-run without redeploying.
- **Feed reconnect loop.** Feeds with `connect()` are retried every 30 s on failure rather than crashing the container.
- **All side effects go through `PersistenceWriter`.** `audit_log` is the canonical event stream the dashboard reads.

### Safety rails (fail-closed)

Multiple layers, all enforced:

1. `broker.mode: live` raises in the pydantic config validator before the engine starts. v1 cannot run live.
2. `PaperAccountGuard` queries `accountSummary()` on boot and refuses unless the IBKR account ID matches `paper_account_allowlist`.
3. `KillSwitchGuard` checks `cfg.risk.kill_switch_file` (default `./KILL`) on every intent. `touch ./KILL` blocks new entries; existing positions still close.
4. `DailyLossLimitGuard`, `MaxOpenPositionsGuard`, `MaxPremiumPctNavGuard` complete the chain.

### Topology

```
┌─ Vercel ────────────────────────┐
│  apps/web/  (Next.js 15)        │ reads from Supabase
└─────────────┬───────────────────┘
              │
┌─ Supabase Postgres ─────────────┐
│  ticks · bars · signals ·       │
│  order_intents · fills ·        │
│  positions · daily_pnl ·        │
│  audit_log · runtime_settings   │
└──▲──────────────▲───────────────┘
   │              │
┌──┴── Railway ──┴────────────────┐  ┌─ Railway ────────────┐
│ market-data-stream              │  │ strategy-engine      │
│ feed → persistence              │  │ feed → indicators    │
└─────────────────────────────────┘  │ → strategy → risk    │
                                     │ → broker → persist   │
                                     └─────────┬────────────┘
                                               ▼
                                     ┌─ Railway ────────────┐
                                     │ ibkr-gateway sidecar │
                                     │ (paper port 4002)    │
                                     └──────────────────────┘
```

A separate `services/backtest_api/` runs alongside the engine on Railway and serves the dashboard's backtest panel.

---

## 2. Build & deploy architecture

### Goals

| Pipeline | Target (warm) | Target (cold lock-changed) |
|----------|---------------|----------------------------|
| GitHub CI overall | < 60 s | < 90 s |
| Railway per-service rebuild | < 15 s | < 90 s |
| Vercel | < 60 s | < 90 s |
| Per-service Docker image | ~150–200 MB | — |

Achieved via four orthogonal levers: **lockfile**, **dep prune**, **multi-stage Dockerfiles with cache mounts**, and **a pre-baked CI image**.

### Dependency graph

The runtime dep tree was aggressively pruned to keep production images small and installs fast:

| Status | Package | Reason |
|--------|---------|--------|
| Kept (prod) | `pydantic`, `pyyaml`, `ib-insync`, `asyncpg`, `fastapi`, `uvicorn[standard]` | Actually imported in non-dev code paths |
| Dropped | `python-dotenv`, `structlog`, `httpx`, `uvloop` | Never imported anywhere |
| Dropped | `supabase` (SDK) | Code uses `asyncpg` directly. SDK pulled ~20 transitive packages (`postgrest`, `pyiceberg`, `pyroaring`, `realtime`, `storage3`, `gotrue`, etc.) |
| Dropped | `scipy` | Used only for `norm.cdf`/`norm.pdf` in `synthetic_options.py`; replaced with stdlib `math.erf`-based functions |
| Moved to `[dev]` | `yfinance`, `pandas` | Free dev/replay path only. `engine/data_feeds/factory.py` imports `YFinanceFeed` lazily so factory remains importable in prod |
| Dev-only | `pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-xdist`, `ruff`, `mypy` | Tests + lint |

**Result:** 1.2 GB → 47 MB prod install. ~150–200 MB final Docker image per service.

### `uv.lock`

Committed to the repo. All Dockerfiles and CI use `uv sync --frozen`, which skips the resolver entirely (~3× faster than `pip install` even cold). Regenerate after any `pyproject.toml` change with `uv lock`.

### Service Dockerfiles (`services/*/Dockerfile`)

All three services (`strategy-engine`, `market-data-stream`, `backtest-api`) follow the same pattern:

```dockerfile
# Builder: install deps from uv.lock into /app/.venv
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_SYSTEM_PYTHON=1
WORKDIR /app
COPY --link pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Runtime: minimal image, only what's needed
FROM python:3.11-slim AS runtime
ENV PYTHONPATH=/app PATH="/app/.venv/bin:$PATH"
RUN apt-get update && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*
COPY --link --from=builder /app/.venv /app/.venv
WORKDIR /app
COPY --link contracts ./contracts
COPY --link config ./config
COPY --link engine ./engine
COPY --link services ./services
CMD ["python", "-m", "services.<name>"]
```

Three things matter:
- **Official `astral-sh/uv` base image** — `uv` is preinstalled, dropping the `pip install uv` step (~5–10 s saved per build).
- **BuildKit cache mount** (`--mount=type=cache,target=/root/.cache/uv`) — survives across builds. Warm rebuilds reuse the uv download cache.
- **`COPY --link`** — layers stay reusable even when an earlier `COPY` invalidates. Big win on Railway across builds.
- **Multi-stage** — runtime image holds only the venv + curl + project source. No `build-essential`, no apt cache. Verified: all remaining deps ship cp311 manylinux wheels.

### CI architecture (`.github/workflows/`)

Three jobs, each with a `paths-filter` gate so they only run when relevant files change:

```
push/PR → changes (paths-filter)
            ├─ python  (if Python paths changed)
            ├─ frontend (if apps/web/** changed)
            └─ migrations (if SQL paths changed)
```

**Python job cache strategy** (in priority order):
1. **`actions/cache` of `.venv`** keyed on `hashFiles('uv.lock')`. Hit → skip install entirely.
2. **Best-effort pull of pre-baked image** `ghcr.io/<owner>/alpha-kite-ci-base:lock-<uv-lock-hash>` — extract `/app/.venv` directly via `docker create` + `docker cp`.
3. **Cold fallback** — `uv sync --frozen --extra dev`. Already ~3× faster than pip even cold.

Tests run as `uv run pytest -m "not live and not supabase" -n auto --maxfail=1 -q`. Process-parallel via `pytest-xdist`; safe because there's no `tests/conftest.py` with shared session-scope state.

**Frontend job cache strategy:**
- `actions/cache` of `apps/web/node_modules` keyed on `package-lock.json`.
- `actions/cache` of `apps/web/.next/cache` with a rolling key + `restore-keys` fallback so partial cache hits still help.
- Install via `npm ci` (deterministic, faster than `npm install`).

**Migrations job:**
- Runs `sqlfluff lint --dialect postgres infra/supabase/migrations`. Replaces a no-op `psql -d "host=/tmp" … || true` predecessor that swallowed all errors.

### Pre-baked CI image (`.github/workflows/prewarm-ci-base.yml`)

Triggered on `push: paths: [pyproject.toml, uv.lock, .github/workflows/prewarm-ci-base.yml]` and `workflow_dispatch`. Builds `.github/ci-base.Dockerfile`:

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_SYSTEM_PYTHON=1
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --extra dev --no-install-project
```

Pushes to:
- `ghcr.io/<owner>/alpha-kite-ci-base:latest`
- `ghcr.io/<owner>/alpha-kite-ci-base:lock-<hash>`
- `ghcr.io/<owner>/alpha-kite-ci-base:cache` (registry cache for cross-run reuse via `cache-to: type=registry,mode=max`)

The CI python job's "try prebaked image" step pulls the `lock-<hash>` tag, so a CI run on a fresh runner — even with no GHA cache — can hydrate the venv in ~5 s instead of ~30 s.

**First run requires GHCR write permission** in the repo settings (Settings → Actions → General → Workflow permissions → "Read and write permissions").

### Vercel (`apps/web/vercel.json` + `next.config.mjs`)

```json
{ "buildCommand": "next build --turbopack", "installCommand": "npm ci --no-audit --no-fund" }
```

```js
const nextConfig = { output: 'standalone', reactStrictMode: true };
```

`output: 'standalone'` reduces deploy size; Turbopack (`next build --turbopack`) is GA in Next 15.5+ and ~30% faster than webpack. Vercel already caches `.next/cache` automatically — realistic ceiling here is ~2×. If a deploy preview breaks under Turbopack, drop the `--turbopack` flag and keep the rest.

### Railway (`infra/railway/*.json`)

Each service has a `watchPatterns` array so a push only rebuilds the services whose source actually changed:

```json
{
  "build": {
    "dockerfilePath": "services/strategy-engine/Dockerfile",
    "watchPatterns": [
      "contracts/**", "config/**", "engine/**",
      "services/strategy_engine/**", "services/strategy-engine/**",
      "services/persistence/**", "pyproject.toml"
    ]
  }
}
```

A frontend-only commit triggers 0 Railway redeploys instead of 3. A change to `engine/strategies/` triggers only `strategy-engine`. A change to `engine/data_feeds/ibkr_live.py` triggers both `strategy-engine` and `market-data-stream`.

### `docker-compose.yml`

Local stack adds `cache_from: [alpha-kite/<service>:dev]` to each Python service's build block, so local rebuilds reuse layers from prior images. Otherwise unchanged from the runtime topology described above.

### Hyphen-vs-underscore service directories

`services/strategy_engine/` (underscore) is the Python package; `services/strategy-engine/` (hyphen) holds the `Dockerfile`. Same for `market-data-stream` and `backtest-api`. Edit code in the underscore dir; build context lives in the hyphen dir. Railway watch patterns intentionally include both spellings.

---

## File index

| Concern | Path |
|---------|------|
| Runtime contracts | `contracts/` |
| Strategy implementations | `engine/strategies/` |
| Data feeds + factory | `engine/data_feeds/` |
| Risk guards + pipeline | `engine/risk/` |
| Brokers | `engine/broker/` |
| Orchestrator | `services/strategy_engine/main.py` |
| Persistence | `services/persistence/` |
| Schema | `infra/supabase/migrations/000{1..4}_*.sql` |
| Service Dockerfiles | `services/{strategy-engine,market-data-stream,backtest-api}/Dockerfile` |
| IBKR sidecar | `infra/ibkr/Dockerfile` |
| CI workflows | `.github/workflows/{ci,prewarm-ci-base}.yml` |
| Pre-baked CI image | `.github/ci-base.Dockerfile` |
| Railway service specs | `infra/railway/*.json` |
| Vercel config | `apps/web/{vercel.json,next.config.mjs}` |
| Lockfile | `uv.lock` |
