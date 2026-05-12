"""Historical bar backfill via IBKR ``reqHistoricalData``.

Pulls bars (1m / 5m / 1h / 1d) backwards from "now" until the requested
``--start`` is reached or IBKR returns an empty chunk (its hard depth limit
for that bar size). Bars land in the same ``bars`` table the live engine
writes into, keyed on ``(symbol, interval_seconds, open_time)`` so re-running
is idempotent.

Pacing
------

IBKR throttles historical-data requests to ~60 per 10 minutes. We sleep
``--pace-seconds`` between calls (default 11s ≈ 55 calls/10min) so we stay
under the limit by a comfortable margin. A pacing violation (err 162) gets
logged and the script backs off for a minute before continuing.

Depth (rule of thumb, varies by subscription)
---------------------------------------------

  * 1 min  — 6-12 months for liquid US equity ETFs (with TotalView).
  * 5 min  — 1-2 years.
  * 1 hour — 2-3 years.
  * 1 day  — 10+ years.

Usage
-----

::

    # Connect to local IBKR Gateway (paper port 4002):
    SUPABASE_DB_URL=... \
        uv run python -m scripts.backfill_bars_ibkr \
            --symbol QQQ --interval 60 --years 2

    # Connect to the Railway-hosted gateway via railway run:
    SUPABASE_DB_URL=... IBKR_HOST=ib-gateway.railway.internal IBKR_PORT=4004 \
        railway run python -m scripts.backfill_bars_ibkr --symbol QQQ --interval 3600

    # Multi-resolution sweep:
    for i in 60 300 3600 86400; do
        uv run python -m scripts.backfill_bars_ibkr --symbol QQQ --interval $i
    done
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from contracts.data_feed import Bar
from services.persistence.storage import SupabaseBackend
from services.persistence.writer import PersistenceWriter

LOG = logging.getLogger("alpha_kite.backfill_ibkr")

_NY = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class _IntervalSpec:
    """IBKR ``barSizeSetting`` and the corresponding ``durationStr`` per call.

    Duration is the lookback per single ``reqHistoricalData`` invocation — we
    set it to the largest value IBKR reliably accepts for each bar size so we
    minimise round-trips against the 60-per-10-min limiter.
    """

    seconds: int
    bar_size: str
    duration: str


# IBKR's documented per-request maxima (Trader Workstation API → "Historical
# Data Limitations"). Picked conservatively so a single call never trips the
# pacing limit by being too large.
_INTERVALS: dict[int, _IntervalSpec] = {
    60:    _IntervalSpec(60,    "1 min",   "1 D"),
    300:   _IntervalSpec(300,   "5 mins",  "1 W"),
    3600:  _IntervalSpec(3600,  "1 hour",  "1 M"),
    86400: _IntervalSpec(86400, "1 day",   "1 Y"),
}


def _primary_exchange(symbol: str) -> str:
    return {"QQQ": "NASDAQ", "SPY": "ARCA", "IWM": "ARCA", "DIA": "ARCA"}.get(
        symbol.upper(), "SMART",
    )


def _format_end_dt(dt: datetime) -> str:
    """IBKR expects ``YYYYMMDD HH:MM:SS US/Eastern`` for ``endDateTime``."""
    return dt.astimezone(_NY).strftime("%Y%m%d %H:%M:%S US/Eastern")


def _bar_to_contract_bar(b: Any, symbol: str, interval_seconds: int) -> Bar | None:
    """Convert an ib_insync ``BarData`` into our ``Bar`` contract row.

    ``b.date`` is either:
      * a naive ``datetime`` (intraday, US/Eastern by IBKR convention), or
      * a ``date`` (daily bars — convert to UTC midnight).

    We coerce both to UTC so all bars land on the same axis the rest of the
    system uses.
    """
    raw = b.date
    if isinstance(raw, datetime):
        if raw.tzinfo is None:
            open_time = raw.replace(tzinfo=_NY).astimezone(UTC)
        else:
            open_time = raw.astimezone(UTC)
    elif isinstance(raw, date):
        open_time = datetime.combine(raw, time(0, 0), tzinfo=UTC)
    else:
        LOG.warning("skip bar with unexpected date type %r: %r", type(raw), raw)
        return None

    vwap = None
    avg = getattr(b, "average", None) or getattr(b, "wap", None)
    if avg is not None and float(avg) > 0:
        vwap = Decimal(str(avg))

    return Bar(
        symbol=symbol,
        interval_seconds=interval_seconds,
        open_time=open_time,
        open=Decimal(str(b.open)),
        high=Decimal(str(b.high)),
        low=Decimal(str(b.low)),
        close=Decimal(str(b.close)),
        volume=int(b.volume) if b.volume and float(b.volume) > 0 else 0,
        vwap=vwap,
    )


async def _pull_chunk(
    ib: Any,
    contract: Any,
    end_dt: datetime,
    spec: _IntervalSpec,
    use_rth: bool,
) -> list[Any]:
    """One ``reqHistoricalDataAsync`` call. Returns ib_insync BarData list."""
    return await ib.reqHistoricalDataAsync(
        contract,
        endDateTime=_format_end_dt(end_dt),
        durationStr=spec.duration,
        barSizeSetting=spec.bar_size,
        whatToShow="TRADES",
        useRTH=use_rth,
        formatDate=1,
    )


async def run(
    symbol: str,
    interval_seconds: int,
    start_dt: datetime,
    end_dt: datetime,
    host: str,
    port: int,
    client_id: int,
    max_requests: int,
    pace_seconds: float,
    use_rth: bool,
) -> dict[str, int]:
    if interval_seconds not in _INTERVALS:
        raise ValueError(
            f"interval_seconds must be one of {sorted(_INTERVALS)}; got {interval_seconds}",
        )
    spec = _INTERVALS[interval_seconds]

    dsn = os.getenv("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError("SUPABASE_DB_URL is required")

    try:
        from ib_insync import IB, Stock  # type: ignore
    except ImportError as exc:
        raise RuntimeError("ib_insync is required (uv sync)") from exc

    backend = SupabaseBackend(dsn)
    writer = PersistenceWriter(backend)

    ib = IB()
    LOG.info("connecting to IBKR at %s:%s (clientId=%s)", host, port, client_id)
    # 30s timeout (default is 4s) — handles public-proxy round-trip latency.
    # Each IBKR handshake step (version, startApi, managedAccounts,
    # nextValidId) is a separate round trip; over the internet via Railway's
    # TCP proxy that easily exceeds 4 s before apiStart fires.
    await ib.connectAsync(host, port, clientId=client_id, timeout=30)
    LOG.info("connected; pulling %s bars for %s back to %s",
             spec.bar_size, symbol, start_dt.isoformat())

    contract = Stock(symbol, _primary_exchange(symbol), "USD")
    await ib.qualifyContractsAsync(contract)

    total_bars = 0
    requests = 0
    cursor = end_dt
    try:
        while requests < max_requests and cursor > start_dt:
            requests += 1
            try:
                ib_bars = await _pull_chunk(ib, contract, cursor, spec, use_rth)
            except Exception as exc:
                # ib_insync surfaces IBKR err 162 (pacing) as a generic
                # exception inside reqHistoricalDataAsync. Back off and retry
                # once; if it fails again we abort and let the user resume.
                LOG.warning("chunk #%d failed (%s); backing off 60s", requests, exc)
                await asyncio.sleep(60)
                try:
                    ib_bars = await _pull_chunk(ib, contract, cursor, spec, use_rth)
                except Exception as exc2:
                    LOG.error("chunk #%d retry failed (%s); stopping", requests, exc2)
                    break

            if not ib_bars:
                LOG.info(
                    "chunk #%d empty — IBKR has no more depth for %s @ %s "
                    "before %s",
                    requests, symbol, spec.bar_size, cursor.isoformat(),
                )
                break

            rows: list[Bar] = []
            for raw in ib_bars:
                converted = _bar_to_contract_bar(raw, symbol, interval_seconds)
                if converted is not None:
                    rows.append(converted)
            if rows:
                await writer.write_bars(rows, feed=f"ibkr_backfill_{spec.bar_size.replace(' ', '')}")
                total_bars += len(rows)

            earliest = min(r.open_time for r in rows) if rows else cursor
            LOG.info(
                "chunk #%d: %d bars, earliest=%s, total=%d",
                requests, len(rows), earliest.isoformat(), total_bars,
            )

            # Step back past the chunk we just got, with a 1-second margin so
            # the boundary bar doesn't get re-requested and double-upserted.
            cursor = earliest - timedelta(seconds=1)
            if cursor <= start_dt:
                break

            await asyncio.sleep(pace_seconds)
    finally:
        try:
            ib.disconnect()
        except Exception:
            pass
        if backend._pool is not None:
            await backend._pool.close()

    return {"requests": requests, "bars": total_bars}


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=UTC)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Backfill historical bars from IBKR into Supabase.",
    )
    parser.add_argument("--symbol", default="QQQ", help="ticker (default: QQQ)")
    parser.add_argument(
        "--interval", type=int, default=60, choices=sorted(_INTERVALS),
        help="bar resolution in seconds (60/300/3600/86400)",
    )
    parser.add_argument(
        "--years", type=float, default=3.0,
        help="how many years of history to attempt (default: 3); ignored if --start given",
    )
    parser.add_argument("--start", type=_parse_date, default=None)
    parser.add_argument("--end", type=_parse_date, default=None)
    parser.add_argument(
        "--ibkr-host", default=os.getenv("IBKR_HOST", "127.0.0.1"),
        help="IBKR Gateway host (default: $IBKR_HOST or 127.0.0.1)",
    )
    parser.add_argument(
        "--ibkr-port", type=int, default=int(os.getenv("IBKR_PORT", "4002")),
        help="IBKR Gateway port (default: $IBKR_PORT or 4002 for paper)",
    )
    parser.add_argument(
        "--client-id", type=int, default=int(os.getenv("IBKR_CLIENT_ID_BACKFILL", "99")),
        help="API client id (default: 99 — distinct from live/strategy ids)",
    )
    parser.add_argument(
        "--max-requests", type=int, default=2000,
        help="safety cap on chunk requests (default: 2000)",
    )
    parser.add_argument(
        "--pace-seconds", type=float, default=11.0,
        help="sleep between chunks to stay under 60-per-10-min (default: 11s)",
    )
    parser.add_argument(
        "--include-extended-hours", action="store_true",
        help="include pre/post-market data (default: regular trading hours only)",
    )
    args = parser.parse_args()

    end_dt = args.end or datetime.now(tz=UTC)
    start_dt = args.start or (end_dt - timedelta(days=int(args.years * 365)))
    if start_dt >= end_dt:
        raise SystemExit("start must be < end")

    counts = asyncio.run(run(
        symbol=args.symbol,
        interval_seconds=args.interval,
        start_dt=start_dt,
        end_dt=end_dt,
        host=args.ibkr_host,
        port=args.ibkr_port,
        client_id=args.client_id,
        max_requests=args.max_requests,
        pace_seconds=args.pace_seconds,
        use_rth=not args.include_extended_hours,
    ))
    LOG.info(
        "done: %d requests, %d bars persisted for %s @ %ds",
        counts["requests"], counts["bars"], args.symbol, args.interval,
    )


if __name__ == "__main__":
    main()
