# alpha-kite-v2

**Buy volatility on QQQ** when the SMA(9) of 1-minute closes crosses the
session VWAP. Pay premium to be long optionality; profit when QQQ realizes
more vol than implied. Paper-trading-first, IBKR-only, code-in-repo.

> v2 swaps the v1 stack: Schwab → IBKR, Lightsail → Railway, 0DTE direction
> → 0DTE long-vol, 1-sec bars → 1-min bars, hard-coded data feed → adapter
> pattern. v1 (Schwab) is preserved in git history but no longer the path.

---

## What's in v1 of v2

* IBKR paper trading via [`ib_insync`](https://github.com/erdewit/ib_insync)
* Strategy: **Buy Volatility on QQQ Crosses** — SMA9/VWAP cross fires →
  ATM 0DTE call (cross up) or put (cross down), or straddle.
* Per-position exits: profit target % / stop loss % / time stop X minutes
  before close.
* Multi-layer fail-closed safety: paper-mode guard, daily-loss limit,
  max-open-positions, on-disk kill switch, dry-run flag.
* Pluggable data adapter — develop free against `yfinance`, replay against
  fixtures, swap to `ibkr_live` only after Phase 2 backtest passes.
* Read-only Next.js dashboard on Vercel.
* Two always-on services on Railway: `strategy-engine` and `market-data-stream`.
* Supabase Postgres for ticks/bars/signals/intents/fills/positions/PnL/audit.

---

## Quick start (15 minutes)

```bash
# 1. clone + install (uv recommended — ~3× faster than pip and uses uv.lock)
git clone https://github.com/MAKaminski/alpha-kite-max
cd alpha-kite-max
uv sync --extra dev          # or: python -m venv .venv && pip install -e '.[dev]'

# 2. run the test suite (parallel via pytest-xdist)
uv run pytest -n auto -m "not live and not supabase"
# 170+ tests should pass in ~1s

# 3. run the end-to-end backtest against a fixture
python scripts/backtest.py \
    --config config/strategy.yaml \
    --fixture tests/fixtures/qqq_2026-04-15_1min.json

# 4. (optional) bring up the full local stack
docker-compose up
```

The default config has `data.feed: yfinance` (free, delayed) and
`broker.dry_run: true` (no orders ever placed). You can run it end-to-end
without spending a dollar.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Vercel — Next.js dashboard (read-only)                     │
│  reads from Supabase                                        │
└──┬──────────────────────────────────────────────────────────┘
   │
┌──┴──────────────────────────────────────────────────────────┐
│  Supabase (Postgres) — ticks, bars, signals,                │
│  order_intents, fills, positions, daily_pnl, audit_log      │
└──▲────────────────────────────▲────────────────────────────┘
   │                             │
┌──┴──────────────────┐  ┌──────┴──────────────────────────┐
│ Railway:            │  │ Railway:                        │
│ market-data-stream  │  │ strategy-engine                 │
│ MarketDataFeed →    │  │ feed → indicators → strategy →  │
│ persistence         │  │ risk → broker → persistence     │
└─────────────────────┘  └────────────────┬────────────────┘
                                          │
                                          ▼
                              ┌────────────────────────────┐
                              │ IBKR Gateway (Docker side- │
                              │ car). Paper port 7497 only │
                              │ in v1.                     │
                              └────────────────────────────┘
```

---

## Repository layout

| Path | Purpose |
|------|---------|
| `contracts/` | Frozen Python interfaces. Every other module imports from here; nothing modifies it. |
| `config/` | Pydantic config schema + the canonical `strategy.yaml`. |
| `engine/indicators/` | Pure-function SMA / VWAP / cross detection. |
| `engine/data_feeds/` | YFinance, IBKR delayed, replay, synthetic options, IBKR live (Phase 3). |
| `engine/strategies/` | `BuyVolQQQCrossStrategy`. |
| `engine/broker/` | `DryRunBroker` (in-memory) + `IBKRPaperBroker` (paper-only). |
| `engine/risk/` | Kill switch, paper guard, daily-loss / max-positions / max-premium guards, pipeline. |
| `services/persistence/` | Async writer + reader; `InMemoryBackend` and `SupabaseBackend`. |
| `services/strategy_engine/` | Orchestrator process — wires everything together. |
| `services/market_data_stream/` | Always-on feed → persistence loop. |
| `apps/web/` | Next.js 15 read-only dashboard. |
| `infra/supabase/migrations/` | `0001_initial.sql`. |
| `infra/railway/` | Per-service Railway deploy specs. |
| `infra/ibkr/` | Gateway sidecar Dockerfile + IBC config templates. |
| `scripts/backtest.py` | Replay-feed-driven expectancy report. |

---

## Strategy parameters (locked v1 numbers)

| Parameter | Value |
|-----------|-------|
| Underlying | QQQ |
| Bar interval | 1 minute |
| SMA period | 9 |
| Reference VWAP | session, RTH |
| Per-trade premium budget | 1 contract @ ~$1.00 ATM (~$100) |
| Profit target | +30% of premium |
| Stop loss | -25% of premium |
| Time stop | exit 30 min before close |
| Max open positions | 1 |
| Daily loss limit | $50 |

Edit `config/strategy.yaml` to change any of these.

---

## Safety rails (non-negotiable)

* **`broker.mode: live` is hard-blocked** at config-load time in v1. The
  pydantic validator raises before the engine even starts.
* **Paper-account guard.** On boot, `IBKRPaperBroker` fetches
  `accountSummary()` and refuses to place orders unless the account ID
  starts with `DU` (IBKR's paper convention) or matches an allowlist
  substring.
* **`broker.dry_run: true`** (default). Strategy emits OrderIntent and
  the engine writes it to `audit_log` — but never calls
  `IB.placeOrder`. Flip to `false` only after the paper guard has been
  proven to refuse a live account.
* **On-disk kill switch.** `touch ./KILL` blocks every new entry until
  the file is removed. Existing positions still close normally.
* **Daily loss limit.** When realized P&L for the day reaches
  `-daily_loss_limit_usd`, every new entry is blocked.

Each guard is **fail-closed**: if it raises, the pipeline blocks.

---

## Phase plan

| Phase | Trigger | What changes |
|-------|---------|--------------|
| **1 — Wiring** *(this release)* | `pytest` + `scripts/backtest.py` both pass against fixture | Plumbing only — proves the chain from feed → fills works deterministically. |
| **2 — Real backtest** | Decision to spend ~$50–$100 on historical 0DTE chain data | Buy historical chain → run replay feed → measure real expectancy across N≥100 trades. |
| **3 — Live paper** | Phase 2 expectancy ≥ +10% per trade | Subscribe IBKR US Securities Snapshot + OPRA Top-of-Book (~$12/mo) → `data.feed: ibkr_live` → `dry_run: false`. |
| **4 — Real money** *(future v2 release)* | 60 days Phase 3, win rate ≥ 70%, expectancy within ±20% of Phase 2 | New release with `mode: live` allowed. |

---

## Out of scope for v1

* Live trading
* Options Alpha integration
* TradeStation integration
* Auto-execution from the web UI
* Multi-symbol strategies
* IBKR live data feed (Phase 3 — single config flip)

---

## Running locally

### Tests

```bash
pytest -n auto                             # everything except live + supabase, in parallel
pytest -m live                             # requires running IB Gateway
pytest -m supabase                         # requires SUPABASE_DB_URL
```

> The free dev path (`yfinance` feed, `pandas`-driven bar parsing) is in the
> `[dev]` extra. Production installs (`pip install .` / `uv sync --no-dev`)
> ship without `yfinance`, `pandas`, or `scipy` — the `factory.py` import is
> lazy, so `data.feed: ibkr_live` works on a 47 MB install.

### Backtest

```bash
python scripts/backtest.py \
    --config config/strategy.yaml \
    --fixture tests/fixtures/qqq_2026-04-15_1min.json
```

### Engine + market-data services (Docker)

```bash
cp .env.example .env       # fill in IBKR + Supabase creds
docker-compose up
```

### Frontend

```bash
cd apps/web
npm install
npm run dev                # http://localhost:3000
```

---

## What's next — manual setup checklist

These are the human-in-the-loop steps the scaffold can't do:

- [ ] Create an IBKR paper account; note the `DU…` account id.
- [ ] Install IBKR Trader Workstation **or** run the Gateway sidecar via
      `docker-compose up ibkr-gateway`. Set `IBKR_TRADING_MODE=paper`.
- [ ] Create a Supabase project. Apply
      `infra/supabase/migrations/0001_initial.sql`. Copy the URL +
      service-role key into `.env`.
- [ ] Create a Railway project; link the two service templates in
      `infra/railway/`.
- [ ] Create a Vercel project linked to `apps/web/`. Set
      `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- [ ] Run `pytest`. Run `python scripts/backtest.py`.
- [ ] Run the engine end-to-end with `dry_run: true` for 1 trading day,
      confirm signals + intents land in `audit_log`.
- [ ] Flip `dry_run: false` only after the paper guard has been
      verified by running the engine with a live account id and
      asserting the start-up `NonPaperAccountError`.
- [ ] After Phase 2 backtest hits +10%/trade with N≥100 trades,
      subscribe to IBKR data ($12/mo), flip `data.feed: ibkr_live`.

---

## Build & deploy performance

Targeted ~10–30× speedup vs the default Python/Docker setup. See
[`architecture.md`](architecture.md) for the full picture.

| Pipeline | Warm | Cold (lock changed) | Image size |
|----------|------|---------------------|------------|
| CI Python job | ~10–15 s | ~25 s | — |
| CI frontend job | ~20 s | ~60 s | — |
| Docker per-service rebuild | ~8–10 s | ~50–70 s | ~150–200 MB |

Levers used:
- **`uv.lock` + `uv sync --frozen`** — skips the resolver, ~3× faster than `pip install`.
- **Aggressive dep prune** — dropped `python-dotenv`, `structlog`, `httpx`, `supabase` SDK, `uvloop`, `scipy`. Moved `yfinance`/`pandas` to `[dev]`. Prod install: 1.2 GB → 47 MB.
- **Multi-stage Dockerfiles** with `FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim`, BuildKit cache mounts, and `COPY --link`.
- **Pre-baked CI image** at `ghcr.io/<owner>/alpha-kite-ci-base:lock-<hash>` — built by `.github/workflows/prewarm-ci-base.yml` on `uv.lock` change; CI extracts the baked `.venv` before falling back to a cold install.
- **Path-filtered CI** (`dorny/paths-filter`) — Python-only commits skip frontend job and vice versa.
- **Railway `watchPatterns`** — most pushes trigger 0 or 1 service rebuilds instead of 3.
- **`pytest -n auto`** — 170 tests in <1 s.

## License

MIT (see [LICENSE](LICENSE)).
