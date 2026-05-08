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
    fixture: str = Field(
        description="Path to the fixture JSON, e.g. tests/fixtures/qqq_2026-04-15_1min.json",
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


@app.post("/run")
async def run(req: RunRequest) -> dict:
    fixture_path = Path(req.fixture)
    if not fixture_path.exists():
        raise HTTPException(status_code=404, detail=f"fixture not found: {req.fixture}")
    config_path = Path(req.config)
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"config not found: {req.config}")

    report = await run_backtest(req.config, req.fixture)

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
        "fixture": req.fixture,
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
