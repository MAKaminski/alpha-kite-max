"""Common base class for ``MarketDataFeed`` implementations."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date

from contracts.data_feed import (
    Bar,
    ChainSnapshot,
    OptionContract,
    OptionQuote,
    Quote,
)


class BaseFeed:
    """Default implementation of the ``MarketDataFeed`` Protocol.

    Subclasses should override the four async streaming/fetch methods.
    The base class only provides a ``name`` attribute and a ``_validate_symbol``
    helper that subclasses can call before initiating a stream.
    """

    name: str = "base"

    @staticmethod
    def _validate_symbol(symbol: str) -> str:
        if not isinstance(symbol, str):
            raise TypeError("symbol must be a string")
        cleaned = symbol.strip().upper()
        if not cleaned:
            raise ValueError("symbol must be a non-empty string")
        return cleaned

    async def stream_equity_quotes(self, symbol: str) -> AsyncIterator[Quote]:
        raise NotImplementedError
        # pragma: no cover - keeps mypy happy that this is an async generator
        if False:
            yield  # type: ignore[unreachable]

    async def stream_equity_bars(
        self, symbol: str, interval_seconds: int = 60
    ) -> AsyncIterator[Bar]:
        raise NotImplementedError
        if False:
            yield  # type: ignore[unreachable]

    async def get_option_chain(self, underlying: str, expiry: date) -> ChainSnapshot:
        raise NotImplementedError

    async def stream_option_quotes(
        self, contracts: list[OptionContract]
    ) -> AsyncIterator[OptionQuote]:
        raise NotImplementedError
        if False:
            yield  # type: ignore[unreachable]
