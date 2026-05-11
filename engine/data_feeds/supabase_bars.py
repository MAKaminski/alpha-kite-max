"""Bar feed that streams 1-min (or other-resolution) bars out of the
``bars`` Supabase table.

Use this with the backtest harness to run the strategy against real
historical data the engine + backfill scripts have already persisted —
no JSON fixture required. The feed is read-only; SyntheticOptionsFeed
still wraps it to produce option chains, exactly like ReplayFeed.

Selecting bars
--------------

Pass ``start`` / ``end`` to bound the time range and ``interval_seconds``
to pick which resolution to replay (``60`` for 1-min, ``300`` for 5-min,
etc.). Rows are streamed in ``open_time`` ascending order so the strategy
sees the same chronology a live engine would.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from contracts.data_feed import (
    Bar,
    ChainSnapshot,
    OptionContract,
    OptionQuote,
    Quote,
)

from engine.data_feeds.base import BaseFeed


class SupabaseBarsFeed(BaseFeed):
    """Stream historical bars from the ``bars`` table for a backtest."""

    name: str = "supabase_bars"

    def __init__(
        self,
        dsn: str,
        symbol: str,
        start: datetime,
        end: datetime,
        interval_seconds: int = 60,
    ) -> None:
        if start >= end:
            raise ValueError("start must be < end")
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self._dsn = dsn
        self._symbol = symbol.upper()
        self._start = start
        self._end = end
        self._interval = int(interval_seconds)
        self._pool: Any | None = None
        self._cached_bars: list[Bar] | None = None

    @property
    def interval_seconds(self) -> int:
        """Bar resolution this feed is loaded for. Exposed so wrappers like
        SyntheticOptionsFeed can match the interval when streaming bars
        (the feed enforces a strict interval match in stream_equity_bars).
        """
        return self._interval

    async def _ensure_pool(self) -> Any:
        if self._pool is None:
            import asyncpg
            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=2)
        return self._pool

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def _load_bars(self) -> list[Bar]:
        if self._cached_bars is not None:
            return self._cached_bars
        pool = await self._ensure_pool()
        sql = (
            "SELECT symbol, interval_seconds, open_time, open, high, low, close, "
            'volume, vwap FROM "bars" WHERE symbol = $1 AND interval_seconds = $2 '
            "AND open_time >= $3 AND open_time < $4 ORDER BY open_time ASC"
        )
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                sql, self._symbol, self._interval, self._start, self._end,
            )
        bars: list[Bar] = []
        for r in rows:
            bars.append(Bar(
                symbol=r["symbol"],
                interval_seconds=int(r["interval_seconds"]),
                open_time=r["open_time"],
                open=Decimal(str(r["open"])),
                high=Decimal(str(r["high"])),
                low=Decimal(str(r["low"])),
                close=Decimal(str(r["close"])),
                volume=int(r["volume"]),
                vwap=(Decimal(str(r["vwap"])) if r["vwap"] is not None else None),
            ))
        self._cached_bars = bars
        return bars

    async def stream_equity_bars(
        self, symbol: str, interval_seconds: int = 60
    ) -> AsyncIterator[Bar]:
        sym = self._validate_symbol(symbol)
        if sym != self._symbol:
            raise ValueError(
                f"feed loaded for {self._symbol}, asked to stream {sym}",
            )
        if interval_seconds != self._interval:
            raise ValueError(
                f"feed loaded for {self._interval}s bars, asked for {interval_seconds}s",
            )
        for bar in await self._load_bars():
            yield bar

    async def stream_equity_quotes(self, symbol: str) -> AsyncIterator[Quote]:
        sym = self._validate_symbol(symbol)
        spread = Decimal("0.01")
        for bar in await self._load_bars():
            yield Quote(
                symbol=sym,
                timestamp=bar.open_time,
                bid=bar.close - spread,
                ask=bar.close + spread,
                last=bar.close,
            )

    async def get_option_chain(self, underlying: str, expiry: date) -> ChainSnapshot:
        sym = self._validate_symbol(underlying)
        # SyntheticOptionsFeed builds the chain from the underlying — we just
        # need to return a non-None ChainSnapshot anchored to the first bar.
        bars = await self._load_bars()
        snapshot_time = (
            bars[0].open_time if bars
            else datetime.combine(expiry, datetime.min.time())
        )
        return ChainSnapshot(
            underlying=sym,
            expiry=expiry,
            snapshot_time=snapshot_time,
            contracts=[],
        )

    async def stream_option_quotes(
        self, contracts: list[OptionContract]
    ) -> AsyncIterator[OptionQuote]:
        raise NotImplementedError(
            "SupabaseBarsFeed has no option data — wrap with SyntheticOptionsFeed",
        )
        if False:  # pragma: no cover - make this an async generator for typing
            yield  # type: ignore[unreachable]


__all__ = ["SupabaseBarsFeed"]
