"""Backfill 1-minute bars from yfinance into the Supabase ``bars`` table.

yfinance gives free intraday data with two important limits:

* 1-minute interval is only available for the last 7 calendar days
  (rolling). Older bars ship at 5/15/30-minute granularity max.
* Returned data is delayed by ~15 min during US market hours.

Usage:

    SUPABASE_DB_URL=postgres://... \
        python -m scripts.backfill_bars --symbol QQQ --days 7

The script is idempotent thanks to the writer's ``upsert`` on
``(symbol, interval_seconds, open_time)`` — re-running it just refreshes
any bars that yfinance has updated.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from contracts.data_feed import Bar
from services.persistence.storage import InMemoryBackend, SupabaseBackend
from services.persistence.writer import PersistenceWriter

LOG = logging.getLogger("alpha_kite.backfill")


def _row_to_bar(symbol: str, ts: datetime, row: dict[str, Any]) -> Bar:
    """Convert one yfinance row into our :class:`Bar` contract."""
    return Bar(
        symbol=symbol,
        interval_seconds=60,
        # yfinance returns timezone-aware US/Eastern datetimes; persist as UTC.
        open_time=ts.astimezone(UTC),
        open=Decimal(str(row["Open"])),
        high=Decimal(str(row["High"])),
        low=Decimal(str(row["Low"])),
        close=Decimal(str(row["Close"])),
        volume=int(row["Volume"]),
        vwap=None,
    )


def _fetch(symbol: str, days: int) -> list[Bar]:
    """Pull the last ``days`` calendar days of 1-min bars from yfinance."""
    import yfinance as yf

    period = f"{days}d"
    LOG.info("yfinance.download(%s, period=%s, interval=1m)", symbol, period)
    df = yf.download(
        symbol,
        period=period,
        interval="1m",
        progress=False,
        auto_adjust=False,
        prepost=False,
    )
    if df is None or df.empty:
        LOG.warning("yfinance returned no rows for %s", symbol)
        return []

    bars: list[Bar] = []
    # When yfinance is given a single ticker it sometimes returns a
    # MultiIndex columns frame ([("Open","QQQ"), ...]). Flatten if so.
    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        df = df.droplevel(1, axis=1)

    for ts, row in df.iterrows():
        try:
            bars.append(_row_to_bar(symbol, ts.to_pydatetime(), dict(row)))
        except Exception as exc:
            LOG.warning("skipped row %s: %s", ts, exc)
    return bars


async def run(symbol: str, days: int, dry_run: bool) -> int:
    if dry_run or not os.getenv("SUPABASE_DB_URL"):
        backend: Any = InMemoryBackend()
        LOG.warning(
            "SUPABASE_DB_URL unset (or --dry-run) — using in-memory backend; "
            "rows will NOT be persisted",
        )
    else:
        backend = SupabaseBackend(os.environ["SUPABASE_DB_URL"])

    writer = PersistenceWriter(backend)
    bars = _fetch(symbol, days)
    LOG.info("writing %d bars for %s", len(bars), symbol)

    written = 0
    for bar in bars:
        await writer.write_bar(bar, feed="yfinance_backfill")
        written += 1

    LOG.info("done — %d bars written", written)
    return written


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="QQQ", help="ticker to backfill (default: QQQ)")
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="calendar days of history to pull (yfinance caps 1m at 7)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="do not connect to Supabase; print row counts only",
    )
    args = parser.parse_args()

    if args.days > 7:
        LOG.warning(
            "yfinance only supplies 1-min bars for the last 7 days; "
            "requested %d will be clipped",
            args.days,
        )

    started = datetime.now(UTC)
    written = asyncio.run(run(args.symbol, args.days, args.dry_run))
    elapsed = (datetime.now(UTC) - started) - timedelta(microseconds=0)
    LOG.info("backfill finished in %s — %d rows", elapsed, written)


if __name__ == "__main__":
    main()
