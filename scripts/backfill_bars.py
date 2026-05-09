"""Multi-resolution historical bar backfill from yfinance into Supabase.

yfinance free-tier ceilings (per Yahoo's documented limits, summer 2026):

  * 1-minute bars  — 7 calendar days max (rolling).
  * 5-minute bars  — 60 calendar days max.
  * 1-hour bars    — 730 calendar days (~2 years) max.
  * 1-day bars     — effectively unlimited; we cap at 5 years per user spec.

Running this script pulls each resolution within its respective ceiling and
upserts every row into the ``bars`` table. Because the writer keys on
``(symbol, interval_seconds, open_time)``, each resolution lives in its own
slice of the table without conflict, and re-running just refreshes whatever
yfinance has updated.

Usage::

    SUPABASE_DB_URL=postgres://... \
        python -m scripts.backfill_bars --symbol QQQ

    # Restrict to a single resolution:
    python -m scripts.backfill_bars --symbol SPY --intervals 1d

    # Quick check without touching Supabase:
    python -m scripts.backfill_bars --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from contracts.data_feed import Bar
from services.persistence.storage import InMemoryBackend, SupabaseBackend
from services.persistence.writer import PersistenceWriter

LOG = logging.getLogger("alpha_kite.backfill")


@dataclass(frozen=True)
class Resolution:
    """One yfinance pull spec.

    ``interval`` is the yfinance-style label (``1m``, ``5m``, ``1h``, ``1d``);
    ``period`` is the lookback string (``7d``, ``60d``, ``730d``, ``5y``);
    ``interval_seconds`` is what we persist into the bars table so the chart
    layer can disambiguate resolutions for a single ``(symbol, open_time)``.
    """

    interval: str
    period: str
    interval_seconds: int


# yfinance free-tier ceilings — pulling beyond these silently clips on Yahoo's
# end. We pull right at the ceiling so the user gets max history per cell.
RESOLUTIONS: tuple[Resolution, ...] = (
    Resolution(interval="1m", period="7d", interval_seconds=60),
    Resolution(interval="5m", period="60d", interval_seconds=300),
    Resolution(interval="1h", period="730d", interval_seconds=3_600),
    Resolution(interval="1d", period="5y", interval_seconds=86_400),
)


def _row_to_bar(symbol: str, interval_seconds: int, ts: datetime,
                row: dict[str, Any]) -> Bar:
    """Convert one yfinance row to our :class:`Bar` contract."""
    return Bar(
        symbol=symbol,
        interval_seconds=interval_seconds,
        # yfinance returns timezone-aware US/Eastern datetimes for intraday
        # and naive UTC midnight for daily. Coerce both to UTC.
        open_time=ts.astimezone(UTC) if ts.tzinfo else ts.replace(tzinfo=UTC),
        open=Decimal(str(row["Open"])),
        high=Decimal(str(row["High"])),
        low=Decimal(str(row["Low"])),
        close=Decimal(str(row["Close"])),
        volume=int(row["Volume"]) if row.get("Volume") else 0,
        vwap=None,
    )


def _fetch(symbol: str, res: Resolution) -> list[Bar]:
    """Pull one resolution from yfinance and yield Bars."""
    import yfinance as yf

    LOG.info(
        "yfinance.download(%s, period=%s, interval=%s)",
        symbol, res.period, res.interval,
    )
    df = yf.download(
        symbol,
        period=res.period,
        interval=res.interval,
        progress=False,
        auto_adjust=False,
        prepost=False,
    )
    if df is None or df.empty:
        LOG.warning("no rows returned for %s @ %s", symbol, res.interval)
        return []

    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        # When given a single ticker, newer yfinance versions emit a MultiIndex
        # column frame. Flatten the second level.
        df = df.droplevel(1, axis=1)

    bars: list[Bar] = []
    for ts, row in df.iterrows():
        try:
            ts_py = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
            bars.append(_row_to_bar(symbol, res.interval_seconds, ts_py, dict(row)))
        except Exception as exc:
            LOG.warning("[%s @ %s] skipped row %s: %s", symbol, res.interval, ts, exc)
    return bars


async def run(symbol: str, intervals: list[str], dry_run: bool) -> dict[str, int]:
    """Pull every requested resolution and upsert into the bars table."""
    if dry_run or not os.getenv("SUPABASE_DB_URL"):
        backend: Any = InMemoryBackend()
        LOG.warning(
            "SUPABASE_DB_URL unset (or --dry-run) — using in-memory backend; "
            "rows will NOT be persisted",
        )
    else:
        backend = SupabaseBackend(os.environ["SUPABASE_DB_URL"])

    writer = PersistenceWriter(backend)
    counts: dict[str, int] = {}

    for res in RESOLUTIONS:
        if res.interval not in intervals:
            continue
        bars = _fetch(symbol, res)
        if bars:
            await writer.write_bars(bars, feed=f"yfinance_backfill_{res.interval}")
        counts[res.interval] = len(bars)
        LOG.info("[%s @ %s] %d bars persisted", symbol, res.interval, len(bars))

    return counts


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Multi-resolution historical bar backfill from yfinance.",
    )
    parser.add_argument(
        "--symbol", default="QQQ",
        help="ticker to backfill (default: QQQ)",
    )
    parser.add_argument(
        "--intervals",
        nargs="+",
        choices=[r.interval for r in RESOLUTIONS],
        default=[r.interval for r in RESOLUTIONS],
        help="which resolutions to pull; default is all four (1m/5m/1h/1d)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="don't connect to Supabase; print yfinance row counts only",
    )
    args = parser.parse_args()

    started = datetime.now(UTC)
    counts = asyncio.run(run(args.symbol, args.intervals, args.dry_run))
    elapsed = (datetime.now(UTC) - started) - timedelta(microseconds=0)

    total = sum(counts.values())
    summary = ", ".join(f"{k}={v}" for k, v in counts.items())
    LOG.info("backfill finished in %s — %d rows total (%s)",
             elapsed, total, summary)


if __name__ == "__main__":
    main()
