"""Backfill historical SMA/VWAP cross signals from persisted bars.

Reads ``bars`` for a symbol+interval+date-range, computes session VWAP and
SMA(N), detects sign-change crosses in ``sma - vwap``, and writes one row per
cross into the ``signals`` table tagged with ``metadata.scope = "security"``.

These rows describe the *security* (an indicator-level observation), not a
portfolio decision. The live engine still emits its own crosses with
``metadata.scope = "portfolio"`` when it actually decides to enter a trade.
The chart reads both today, but the ``scope`` tag is the bifurcation point so
the UI / risk layer can later split indicator-only crosses from real entries.

Idempotent: re-running deletes prior security-scope rows for the same
``(strategy, symbol, ts-range)`` triplet before inserting the fresh set, so
the table never accumulates duplicates from repeated runs.

Usage::

    SUPABASE_DB_URL=postgres://... \
        python -m scripts.backfill_signals --symbol QQQ --interval 60

    # Restrict to a date range (UTC, inclusive of start, exclusive of end):
    python -m scripts.backfill_signals --symbol QQQ --interval 60 \
        --start 2026-05-01 --end 2026-05-11

    # Different SMA period:
    python -m scripts.backfill_signals --symbol QQQ --sma-period 20
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

from services.persistence.storage import SupabaseBackend

LOG = logging.getLogger("alpha_kite.backfill_signals")

# Strategy name embedded in the row's ``strategy`` column. Distinct from any
# live strategy name (e.g. ``buy_vol_qqq_cross``) so a future query can split
# "indicator observations" from "strategy decisions" without needing to peek
# into metadata.
_STRATEGY_PREFIX = "sma_vwap_cross_indicator"


@dataclass(frozen=True)
class _Bar:
    open_time: datetime
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    vwap: Decimal | None


def _strategy_name(sma_period: int) -> str:
    return f"{_STRATEGY_PREFIX}_sma{sma_period}"


def _utc_day(ts: datetime) -> str:
    return ts.astimezone(UTC).strftime("%Y-%m-%d")


def _compute_sma(bars: list[_Bar], period: int) -> dict[datetime, Decimal]:
    """Trailing simple moving average over bar closes, keyed by open_time."""
    out: dict[datetime, Decimal] = {}
    if period <= 0:
        return out
    rolling: list[Decimal] = []
    total = Decimal("0")
    for b in bars:
        rolling.append(b.close)
        total += b.close
        if len(rolling) > period:
            total -= rolling.pop(0)
        if len(rolling) == period:
            out[b.open_time] = total / Decimal(period)
    return out


def _compute_vwap(bars: list[_Bar]) -> dict[datetime, Decimal]:
    """Session VWAP from typical price * volume. Numerator/denominator reset
    at every UTC date boundary so multi-day ranges don't blend yesterday's
    flow into today's VWAP. If the bar carries its own ``vwap`` from the feed,
    that wins over the locally computed value.
    """
    out: dict[datetime, Decimal] = {}
    pv = Decimal("0")
    vol = Decimal("0")
    cur_day: str | None = None
    for b in bars:
        day = _utc_day(b.open_time)
        if day != cur_day:
            pv = Decimal("0")
            vol = Decimal("0")
            cur_day = day
        if b.vwap is not None:
            out[b.open_time] = b.vwap
            continue
        typical = (b.high + b.low + b.close) / Decimal("3")
        pv += typical * Decimal(b.volume)
        vol += Decimal(b.volume)
        out[b.open_time] = (pv / vol) if vol > 0 else b.close
    return out


def _detect_crosses(
    bars: list[_Bar],
    sma: dict[datetime, Decimal],
    vwap: dict[datetime, Decimal],
) -> list[dict[str, Any]]:
    """Walk the bars and emit one cross row each time ``sma - vwap`` flips
    sign relative to the previous bar. Resets at UTC-day boundaries — an
    overnight gap is not a cross.
    """
    rows: list[dict[str, Any]] = []
    prev_diff: Decimal | None = None
    cur_day: str | None = None
    for b in bars:
        day = _utc_day(b.open_time)
        if day != cur_day:
            prev_diff = None
            cur_day = day
        s = sma.get(b.open_time)
        v = vwap.get(b.open_time)
        if s is None or v is None:
            continue
        diff = s - v
        if prev_diff is not None and prev_diff != 0 and diff != 0:
            if prev_diff < 0 < diff:
                rows.append(_signal_row(b, s, v, "LONG_VOL_UP"))
            elif prev_diff > 0 > diff:
                rows.append(_signal_row(b, s, v, "LONG_VOL_DOWN"))
        prev_diff = diff
    return rows


def _signal_row(
    bar: _Bar, sma_value: Decimal, vwap_value: Decimal, direction: str,
) -> dict[str, Any]:
    return {
        "ts": bar.open_time,
        "direction": direction,
        "strength": "1",
        "metadata": {
            "source": "indicator_backfill",
            "scope": "security",
            "sma": f"{sma_value:.6f}",
            "vwap": f"{vwap_value:.6f}",
            "close": f"{bar.close:.6f}",
        },
    }


async def _fetch_bars(
    backend: SupabaseBackend,
    symbol: str,
    interval_seconds: int,
    start: datetime,
    end: datetime,
) -> list[_Bar]:
    pool = await backend._ensure_pool()
    sql = (
        'SELECT open_time, high, low, close, volume, vwap FROM "bars" '
        "WHERE symbol = $1 AND interval_seconds = $2 "
        "AND open_time >= $3 AND open_time < $4 "
        "ORDER BY open_time ASC"
    )
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, symbol, interval_seconds, start, end)
    bars: list[_Bar] = []
    for r in rows:
        bars.append(_Bar(
            open_time=r["open_time"],
            high=Decimal(str(r["high"])),
            low=Decimal(str(r["low"])),
            close=Decimal(str(r["close"])),
            volume=int(r["volume"]),
            vwap=(Decimal(str(r["vwap"])) if r["vwap"] is not None else None),
        ))
    return bars


async def _purge_existing(
    backend: SupabaseBackend,
    strategy: str,
    symbol: str,
    start: datetime,
    end: datetime,
) -> int:
    """Delete prior security-scope rows so re-running is idempotent. Scoped
    by metadata->>'scope' so we never touch live (portfolio-scope) writes
    even if a future build picks the same strategy name.
    """
    pool = await backend._ensure_pool()
    sql = (
        'DELETE FROM "signals" WHERE strategy = $1 AND symbol = $2 '
        "AND ts >= $3 AND ts < $4 "
        "AND COALESCE(metadata->>'scope', '') = 'security'"
    )
    async with pool.acquire() as conn:
        result = await conn.execute(sql, strategy, symbol, start, end)
    # asyncpg returns "DELETE <n>"
    try:
        return int(result.split()[-1])
    except (ValueError, IndexError):
        return 0


async def _insert_signals(
    backend: SupabaseBackend,
    strategy: str,
    symbol: str,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return
    payload = [
        {"strategy": strategy, "symbol": symbol, **r} for r in rows
    ]
    await backend.insert("signals", payload)


async def run(
    symbol: str,
    interval_seconds: int,
    start: datetime,
    end: datetime,
    sma_period: int,
) -> dict[str, int]:
    dsn = os.getenv("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError("SUPABASE_DB_URL is required")
    backend = SupabaseBackend(dsn)
    try:
        bars = await _fetch_bars(backend, symbol, interval_seconds, start, end)
        LOG.info("loaded %d bars for %s @ %ds [%s, %s)",
                 len(bars), symbol, interval_seconds, start, end)
        if not bars:
            return {"bars": 0, "crosses": 0, "deleted": 0}
        sma = _compute_sma(bars, sma_period)
        vwap = _compute_vwap(bars)
        crosses = _detect_crosses(bars, sma, vwap)
        LOG.info("detected %d crosses (sma%d/vwap)", len(crosses), sma_period)

        strategy = _strategy_name(sma_period)
        deleted = await _purge_existing(backend, strategy, symbol, start, end)
        LOG.info("purged %d prior security-scope rows for %s", deleted, strategy)
        await _insert_signals(backend, strategy, symbol, crosses)
        return {"bars": len(bars), "crosses": len(crosses), "deleted": deleted}
    finally:
        if backend._pool is not None:
            await backend._pool.close()


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=UTC)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Backfill historical SMA/VWAP cross signals into Supabase.",
    )
    parser.add_argument("--symbol", default="QQQ", help="ticker (default: QQQ)")
    parser.add_argument(
        "--interval", type=int, default=60,
        help="bar resolution in seconds (default: 60 for 1-min)",
    )
    parser.add_argument(
        "--sma-period", type=int, default=9,
        help="SMA period in bars (default: 9)",
    )
    parser.add_argument(
        "--start", type=_parse_date, default=None,
        help="UTC start date YYYY-MM-DD (inclusive); default: 7 days ago",
    )
    parser.add_argument(
        "--end", type=_parse_date, default=None,
        help="UTC end date YYYY-MM-DD (exclusive); default: tomorrow",
    )
    args = parser.parse_args()

    end = args.end or (datetime.now(tz=UTC).replace(hour=0, minute=0, second=0,
                                                    microsecond=0) + timedelta(days=1))
    start = args.start or (end - timedelta(days=7))

    counts = asyncio.run(run(args.symbol, args.interval, start, end, args.sma_period))
    LOG.info(
        "done: %d bars scanned, %d crosses written, %d prior rows purged",
        counts["bars"], counts["crosses"], counts["deleted"],
    )


if __name__ == "__main__":
    main()
