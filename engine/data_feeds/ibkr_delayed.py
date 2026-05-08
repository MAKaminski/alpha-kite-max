"""Interactive Brokers delayed market-data feed (Phase 1 stub)."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
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

logger = logging.getLogger(__name__)


class IBKRDelayedFeed(BaseFeed):
    """Phase 1 stub — use ib_insync delayed mode (no subscription required).

    Tests are skipped with ``@pytest.mark.live`` because this feed cannot
    operate without a running IB Gateway. The implementation here is
    intentionally minimal: it knows how to ``connect``/``disconnect`` and
    will raise ``RuntimeError("not connected")`` when streaming methods are
    called before connection.
    """

    name: str = "ibkr_delayed"

    # Market-data type 3 = delayed (no subscription required).
    DELAYED_MARKET_DATA_TYPE: int = 3

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 17,
    ) -> None:
        self._host = host
        self._port = port
        self._client_id = client_id
        self._ib: Any = None  # ib_insync.IB instance once connected.
        self._connected: bool = False

    async def connect(self) -> None:
        try:
            from ib_insync import IB  # type: ignore
        except ImportError as exc:  # pragma: no cover - dep is in pyproject
            raise RuntimeError("ib_insync is required for IBKRDelayedFeed") from exc

        self._ib = IB()
        await self._ib.connectAsync(self._host, self._port, clientId=self._client_id)
        self._ib.reqMarketDataType(self.DELAYED_MARKET_DATA_TYPE)
        self._connected = True
        logger.info(
            "IBKRDelayedFeed connected to %s:%s (clientId=%s)",
            self._host,
            self._port,
            self._client_id,
        )

    async def disconnect(self) -> None:
        if self._ib is not None and self._connected:
            self._ib.disconnect()
        self._connected = False
        self._ib = None

    def _require_connection(self) -> Any:
        if not self._connected or self._ib is None:
            raise RuntimeError("not connected")
        return self._ib

    async def stream_equity_quotes(self, symbol: str) -> AsyncIterator[Quote]:
        sym = self._validate_symbol(symbol)
        ib = self._require_connection()
        try:
            from ib_insync import Stock  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("ib_insync is required for IBKRDelayedFeed") from exc

        contract = Stock(sym, "SMART", "USD")
        ticker = ib.reqMktData(contract, "", False, False)
        try:
            while True:
                await ib.updateEvent  # wait for next IB tick
                if ticker.bid is None or ticker.ask is None:
                    continue
                yield Quote(
                    symbol=sym,
                    timestamp=datetime.now(tz=UTC),
                    bid=Decimal(str(ticker.bid)),
                    ask=Decimal(str(ticker.ask)),
                    last=Decimal(str(ticker.last)) if ticker.last else None,
                )
        finally:
            ib.cancelMktData(contract)

    async def stream_equity_bars(
        self, symbol: str, interval_seconds: int = 60
    ) -> AsyncIterator[Bar]:
        sym = self._validate_symbol(symbol)
        ib = self._require_connection()
        try:
            from ib_insync import Stock  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("ib_insync is required for IBKRDelayedFeed") from exc

        contract = Stock(sym, "SMART", "USD")
        bars = ib.reqRealTimeBars(contract, interval_seconds, "TRADES", False)
        try:
            for bar in bars:
                yield Bar(
                    symbol=sym,
                    interval_seconds=interval_seconds,
                    open_time=datetime.fromtimestamp(bar.time.timestamp(), tz=UTC),
                    open=Decimal(str(bar.open_)),
                    high=Decimal(str(bar.high)),
                    low=Decimal(str(bar.low)),
                    close=Decimal(str(bar.close)),
                    volume=int(bar.volume),
                )
        finally:
            ib.cancelRealTimeBars(bars)

    async def get_option_chain(self, underlying: str, expiry: date) -> ChainSnapshot:
        sym = self._validate_symbol(underlying)
        self._require_connection()
        # Phase 1 stub: return empty snapshot. Real implementation will be
        # filled in when the live IBKR feed lands in Phase 3.
        return ChainSnapshot(
            underlying=sym,
            expiry=expiry,
            snapshot_time=datetime.now(tz=UTC),
            contracts=[],
        )

    async def stream_option_quotes(
        self, contracts: list[OptionContract]
    ) -> AsyncIterator[OptionQuote]:
        self._require_connection()
        raise NotImplementedError(
            "IBKRDelayedFeed option streaming is deferred to Phase 3"
        )
        if False:  # pragma: no cover - make this an async generator for typing
            yield  # type: ignore[unreachable]
