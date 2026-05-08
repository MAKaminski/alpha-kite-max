"""FastAPI sidecar that exposes ``scripts/backtest.run_backtest`` over HTTP.

The web app (Vercel) doesn't have Python at runtime; it can only call out
via ``fetch()``. This service bridges the gap: POST ``/run`` with a fixture
filename + optional split_date and get a JSON report back.

Deploy as a Railway service alongside ``strategy_engine`` and
``market_data_stream``. Set ``BACKTEST_API_URL`` on Vercel so the web app
knows where to call.

Endpoints
---------

* ``GET  /healthz``      → ``{ "ok": true }``
* ``GET  /fixtures``     → list of fixture files under ``tests/fixtures/``
* ``POST /run``          → run a backtest, return Report dict (includes
                            in-sample/out-of-sample split when ``split_date``
                            is set)
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from scripts.backtest import run_backtest

DEFAULT_CONFIG = "config/strategy.yaml"
FIXTURES_DIR = Path("tests/fixtures")

app = FastAPI(title="alpha-kite-v2 backtest API", version="0.1.0")

# Permissive CORS — the only legitimate caller is the Vercel web app, but
# users may also hit this from local dev / curl. Lock down with ALLOWED_ORIGIN
# env var if exposing publicly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    """Either ``fixture`` (replay JSON) OR ``symbol``+``start``+``end`` (DB)."""

    # Fixture mode
    fixture: str | None = Field(
        default=None,
        description="Path to the fixture JSON, e.g. tests/fixtures/qqq_2026-04-15_1min.json",
    )
    # DB-bars mode
    symbol: str | None = Field(default=None, description="Symbol to pull from bars table")
    start: str | None = Field(default=None, description="ISO-8601 start timestamp (inclusive)")
    end: str | None = Field(default=None, description="ISO-8601 end timestamp (exclusive)")
    interval_seconds: int = Field(
        default=60, description="Bar interval to replay; matches bars.interval_seconds",
    )

    config: str = Field(default=DEFAULT_CONFIG)
    split_date: str | None = Field(
        default=None,
        description="ISO-8601 timestamp; when present, response includes in-sample/oos partitions",
    )


@app.get("/healthz")
def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.get("/fixtures")
def list_fixtures() -> dict[str, list[str]]:
    """List the fixture files the UI can pick from."""
    if not FIXTURES_DIR.is_dir():
        return {"fixtures": []}
    files = sorted(
        str(p.as_posix())
        for p in FIXTURES_DIR.iterdir()
        if p.suffix == ".json" and p.is_file()
    )
    return {"fixtures": files}


@app.get("/symbols")
async def list_symbols() -> dict:
    """List (symbol, interval_seconds) pairs available in the bars table.

    The /backtest UI uses this to populate the DB-bars-mode dropdowns.
    """
    dsn = os.getenv("SUPABASE_DB_URL")
    if not dsn:
        return {"symbols": [], "error": "SUPABASE_DB_URL not configured"}
    import asyncpg
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT symbol, interval_seconds, "
                "MIN(open_time) AS first_bar, MAX(open_time) AS last_bar, "
                "COUNT(*) AS n_bars "
                "FROM bars GROUP BY symbol, interval_seconds "
                "ORDER BY symbol, interval_seconds"
            )
        return {
            "symbols": [
                {
                    "symbol": r["symbol"],
                    "interval_seconds": int(r["interval_seconds"]),
                    "first_bar": r["first_bar"].isoformat(),
                    "last_bar": r["last_bar"].isoformat(),
                    "n_bars": int(r["n_bars"]),
                }
                for r in rows
            ],
        }
    finally:
        await pool.close()


@app.post("/run")
async def run(req: RunRequest) -> dict:
    config_path = Path(req.config)
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"config not found: {req.config}")

    if req.fixture and (req.symbol or req.start or req.end):
        raise HTTPException(
            status_code=400,
            detail="pass either fixture OR symbol+start+end, not both",
        )
    if not req.fixture and not (req.symbol and req.start and req.end):
        raise HTTPException(
            status_code=400,
            detail="must pass either fixture or symbol+start+end",
        )

    if req.fixture:
        fixture_path = Path(req.fixture)
        if not fixture_path.exists():
            raise HTTPException(status_code=404, detail=f"fixture not found: {req.fixture}")
        report = await run_backtest(req.config, req.fixture)
        source_label: dict = {"fixture": req.fixture}
    else:
        try:
            start_dt = datetime.fromisoformat((req.start or "").replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat((req.end or "").replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"invalid start/end: {exc}") from exc
        report = await run_backtest(
            req.config,
            fixture_path=None,
            symbol=req.symbol,
            start=start_dt,
            end=end_dt,
            interval_seconds=req.interval_seconds,
        )
        source_label = {
            "symbol": req.symbol,
            "start": req.start,
            "end": req.end,
            "interval_seconds": req.interval_seconds,
        }

    # Trade list — kept compact so payloads stay small for the UI.
    trades_payload = [
        {
            "intent_id": str(t.intent_id),
            "entry_ts": t.entry_ts.isoformat(),
            "entry_price": str(t.entry_price),
            "side": t.side.value,
            "right": t.contract.right,
            "strike": str(t.contract.strike),
            "expiry": t.contract.expiry.isoformat(),
            "exit_ts": t.exit_ts.isoformat() if t.exit_ts else None,
            "exit_price": str(t.exit_price) if t.exit_price is not None else None,
            "pnl_pct": str(t.pnl_pct) if t.pnl_pct is not None else None,
            "reason": t.reason,
        }
        for t in report.trades
    ]

    body: dict = {
        **source_label,
        "config": req.config,
        "summary": report.summary(),
        "trades": trades_payload,
    }
    if req.split_date:
        try:
            split_dt = datetime.fromisoformat(req.split_date.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"invalid split_date: {exc}") from exc
        body["split"] = report.split(split_dt)
    return body
