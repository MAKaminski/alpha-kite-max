"""Market data feed contract.

The strategy engine consumes data exclusively through the MarketDataFeed
Protocol. Feed implementations live in `engine/data_feeds/` and are selected
by the `data.feed` config value at runtime.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

OptionRight = Literal["C", "P"]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Quote(_Frozen):
    """NBBO snapshot for an equity symbol."""

    symbol: str
    timestamp: datetime
    bid: Decimal
    ask: Decimal
    last: Decimal | None = None
    volume: int | None = None

    @property
    def mid(self) -> Decimal:
        return (self.bid + self.ask) / Decimal(2)


class Bar(_Frozen):
    """OHLCV bar over a fixed interval. `vwap` is the cumulative session
    VWAP at bar close (None if the feed cannot compute it)."""

    symbol: str
    interval_seconds: int
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    vwap: Decimal | None = None


class OptionContract(_Frozen):
    """Static identification of an option contract."""

    underlying: str
    expiry: date
    strike: Decimal
    right: OptionRight
    multiplier: int = 100
    exchange: str = "SMART"


class OptionQuote(_Frozen):
    """Quote + Greeks snapshot for a single option contract."""

    underlying: str
    expiry: date
    strike: Decimal
    right: OptionRight
    timestamp: datetime
    bid: Decimal
    ask: Decimal
    last: Decimal | None = None
    iv: Decimal | None = None
    delta: Decimal | None = None
    gamma: Decimal | None = None
    theta: Decimal | None = None
    vega: Decimal | None = None

    @property
    def mid(self) -> Decimal:
        return (self.bid + self.ask) / Decimal(2)

    def contract(self) -> OptionContract:
        return OptionContract(
            underlying=self.underlying,
            expiry=self.expiry,
            strike=self.strike,
            right=self.right,
        )


class ChainSnapshot(_Frozen):
    """A single-instant view of a chain expiry."""

    underlying: str
    expiry: date
    snapshot_time: datetime
    contracts: list[OptionContract] = Field(default_factory=list)


@runtime_checkable
class MarketDataFeed(Protocol):
    """Read-only stream of equity + option market data.

    All methods are async iterators or async returning. Implementations must
    be safe to call concurrently for distinct symbols/contracts. Implementations
    must NEVER mutate or persist data themselves; pipeline writers do that.
    """

    name: str

    async def stream_equity_quotes(
        self, symbol: str
    ) -> AsyncIterator[Quote]:  # pragma: no cover - protocol
        ...

    async def stream_equity_bars(
        self, symbol: str, interval_seconds: int
    ) -> AsyncIterator[Bar]:  # pragma: no cover - protocol
        ...

    async def get_option_chain(
        self, underlying: str, expiry: date
    ) -> ChainSnapshot:  # pragma: no cover - protocol
        ...

    async def stream_option_quotes(
        self, contracts: list[OptionContract]
    ) -> AsyncIterator[OptionQuote]:  # pragma: no cover - protocol
        ...
