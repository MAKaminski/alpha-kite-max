"""Replay feed — yields recorded bars from a JSON fixture file."""

from __future__ import annotations

import asyncio
import json
import random
from collections.abc import AsyncIterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from contracts.data_feed import (
    Bar,
    ChainSnapshot,
    OptionContract,
    OptionQuote,
    Quote,
)

from engine.data_feeds.base import BaseFeed


class ReplayFeed(BaseFeed):
    """Replay a fixture of historical 1-minute bars deterministically.

    Fixture format::

        {"date": "YYYY-MM-DD", "symbol": "QQQ", "bars": [<Bar dicts>]}

    With ``speed=0`` (the default), the feed yields all bars without
    sleeping (deterministic for unit tests). With ``speed > 0``, the feed
    sleeps ``60/speed`` seconds between bars (e.g. speed=60 → real time).
    ``jitter_seconds`` adds a uniform random jitter on top of the sleep
    when speed > 0.
    """

    name: str = "replay"

    def __init__(
        self,
        path: str | Path,
        speed: float = 0.0,
        jitter_seconds: float = 0.0,
    ) -> None:
        self._path = Path(path)
        if not self._path.exists():
            raise FileNotFoundError(f"replay fixture not found: {self._path}")
        if speed < 0:
            raise ValueError("speed must be >= 0")
        if jitter_seconds < 0:
            raise ValueError("jitter_seconds must be >= 0")
        self._speed = float(speed)
        self._jitter = float(jitter_seconds)
        self._payload: dict[str, Any] = json.loads(self._path.read_text(encoding="utf-8"))

    @property
    def fixture_date(self) -> date:
        return date.fromisoformat(self._payload["date"])

    @property
    def fixture_symbol(self) -> str:
        return str(self._payload["symbol"])

    def _iter_bars(self) -> list[Bar]:
        bars: list[Bar] = []
        for raw in self._payload.get("bars", []):
            bars.append(
                Bar(
                    symbol=raw["symbol"],
                    interval_seconds=int(raw["interval_seconds"]),
                    open_time=datetime.fromisoformat(raw["open_time"]),
                    open=Decimal(str(raw["open"])),
                    high=Decimal(str(raw["high"])),
                    low=Decimal(str(raw["low"])),
                    close=Decimal(str(raw["close"])),
                    volume=int(raw["volume"]),
                    vwap=(Decimal(str(raw["vwap"])) if raw.get("vwap") is not None else None),
                )
            )
        return bars

    async def _maybe_sleep(self, interval_seconds: int) -> None:
        if self._speed <= 0:
            return
        base = interval_seconds / self._speed
        jitter = (
            random.uniform(-self._jitter, self._jitter)
            if self._jitter > 0
            else 0.0
        )
        delay = max(0.0, base + jitter)
        if delay > 0:
            await asyncio.sleep(delay)

    async def stream_equity_bars(
        self, symbol: str, interval_seconds: int = 60
    ) -> AsyncIterator[Bar]:
        sym = self._validate_symbol(symbol)
        if sym != self.fixture_symbol.upper():
            raise ValueError(
                f"replay fixture is for {self.fixture_symbol}, not {sym}"
            )
        first = True
        for bar in self._iter_bars():
            if not first:
                await self._maybe_sleep(bar.interval_seconds)
            first = False
            yield bar

    async def stream_equity_quotes(self, symbol: str) -> AsyncIterator[Quote]:
        sym = self._validate_symbol(symbol)
        if sym != self.fixture_symbol.upper():
            raise ValueError(
                f"replay fixture is for {self.fixture_symbol}, not {sym}"
            )
        spread = Decimal("0.01")
        first = True
        for bar in self._iter_bars():
            if not first:
                await self._maybe_sleep(bar.interval_seconds)
            first = False
            yield Quote(
                symbol=sym,
                timestamp=bar.open_time,
                bid=bar.close - spread,
                ask=bar.close + spread,
                last=bar.close,
            )

    async def get_option_chain(self, underlying: str, expiry: date) -> ChainSnapshot:
        sym = self._validate_symbol(underlying)
        # Replay only carries equity bars; let SyntheticOptionsFeed fill in
        # chain construction.
        snapshot_time = datetime.combine(self.fixture_date, datetime.min.time())
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
            "ReplayFeed has no option data — wrap with SyntheticOptionsFeed"
        )
        if False:  # pragma: no cover - make this an async generator for typing
            yield  # type: ignore[unreachable]
