"""Interactive Brokers LIVE market-data feed (Phase 3).

Requires:
  * Active IBKR data subscription: "US Equity and Options Add-On Streaming
    Bundle" (covers QQQ NBBO + OPRA options) — non-pro pricing ~$4.50/mo.
  * Running IB Gateway / TWS reachable at host:port (paper port 7497).

Connectivity / lifecycle is intentionally similar to ``IBKRDelayedFeed``:
the feed knows nothing about strategy logic, only how to surface
contracts.data_feed types from ib_insync events. The orchestrator drives
all coordination.

This feed sets ``reqMarketDataType(1)`` (real-time) on connect. If the
account doesn't have an active subscription IBKR auto-falls-back to
delayed (type=3) and emits a console message; live calls will succeed
but be 15 minutes stale. A live STARTUP audit row records the actual
data-type returned so dashboards can flag the difference.
"""

from __future__ import annotations

import asyncio
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


def _to_decimal(x: Any) -> Decimal | None:
    """Convert ib_insync's NaN/None/float-ish values to Decimal | None."""
    if x is None:
        return None
    try:
        s = str(x)
        if s.lower() in ("nan", "inf", "-inf"):
            return None
        return Decimal(s)
    except (ValueError, ArithmeticError):
        return None


class IBKRLiveFeed(BaseFeed):
    """Real-time NBBO + OPRA option quotes via ib_insync."""

    name: str = "ibkr_live"

    LIVE_MARKET_DATA_TYPE: int = 1   # 1=live, 2=frozen, 3=delayed, 4=delayed-frozen
    GENERIC_TICK_GREEKS: str = "106"  # OptionImpliedVolatility + Greeks

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 17,
    ) -> None:
        self._host = host
        self._port = port
        self._client_id = client_id
        self._ib: Any = None
        self._connected: bool = False
        self._data_type_returned: int | None = None

    # ───────────────────────────────────────────────────── lifecycle ────

    async def connect(self) -> None:
        try:
            from ib_insync import IB  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("ib_insync is required for IBKRLiveFeed") from exc

        self._ib = IB()
        await self._ib.connectAsync(self._host, self._port, clientId=self._client_id)
        self._ib.reqMarketDataType(self.LIVE_MARKET_DATA_TYPE)
        self._connected = True
        logger.info(
            "IBKRLiveFeed connected to %s:%s (clientId=%s, mktDataType=%s)",
            self._host, self._port, self._client_id, self.LIVE_MARKET_DATA_TYPE,
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

    # ──────────────────────────────────────────────── equity streams ────

    async def stream_equity_quotes(self, symbol: str) -> AsyncIterator[Quote]:
        sym = self._validate_symbol(symbol)
        ib = self._require_connection()
        try:
            from ib_insync import Stock  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("ib_insync is required for IBKRLiveFeed") from exc

        contract = Stock(sym, "SMART", "USD")
        ticker = ib.reqMktData(contract, "", False, False)
        try:
            while True:
                await ib.updateEvent
                bid = _to_decimal(ticker.bid)
                ask = _to_decimal(ticker.ask)
                if bid is None or ask is None:
                    continue
                yield Quote(
                    symbol=sym,
                    timestamp=datetime.now(tz=UTC),
                    bid=bid,
                    ask=ask,
                    last=_to_decimal(ticker.last),
                    volume=int(ticker.volume) if ticker.volume else None,
                )
        finally:
            ib.cancelMktData(contract)

    async def stream_equity_bars(
        self, symbol: str, interval_seconds: int = 60
    ) -> AsyncIterator[Bar]:
        """5-second native bars from IBKR; downsampled if interval_seconds>5.

        IBKR's reqRealTimeBars only supports 5-second bars. Larger intervals
        are aggregated locally.
        """
        sym = self._validate_symbol(symbol)
        ib = self._require_connection()
        try:
            from ib_insync import Stock  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("ib_insync is required for IBKRLiveFeed") from exc

        contract = Stock(sym, "SMART", "USD")
        bars = ib.reqRealTimeBars(contract, 5, "TRADES", False)
        agg_seconds = max(interval_seconds, 5)
        ratio = agg_seconds // 5

        try:
            buf: list[Any] = []
            while True:
                await ib.updateEvent
                # ib_insync reqRealTimeBars returns a list-like RealTimeBarList
                # that grows in place; emit only newly-appended bars.
                if len(bars) == 0:
                    continue
                latest = bars[-1]
                buf.append(latest)
                # Drop dupes — reqRealTimeBars sometimes pushes the same bar
                # multiple times during partial updates.
                if len(buf) >= 2 and buf[-2].time == buf[-1].time:
                    buf.pop()
                    continue
                if len(buf) < ratio:
                    continue
                window = buf[-ratio:]
                first, last = window[0], window[-1]
                yield Bar(
                    symbol=sym,
                    interval_seconds=agg_seconds,
                    open_time=datetime.fromtimestamp(first.time.timestamp(), tz=UTC),
                    open=Decimal(str(first.open_)),
                    high=Decimal(str(max(b.high for b in window))),
                    low=Decimal(str(min(b.low for b in window))),
                    close=Decimal(str(last.close)),
                    volume=int(sum(b.volume for b in window)),
                )
                buf = []
        finally:
            ib.cancelRealTimeBars(bars)

    # ──────────────────────────────────────────────── option streams ────

    async def get_option_chain(self, underlying: str, expiry: date) -> ChainSnapshot:
        """Build OptionContracts for the requested expiry's ATM ±5 strikes.

        Uses reqSecDefOptParams to discover available strikes, then picks the
        five strikes nearest the underlying's last trade price.
        """
        sym = self._validate_symbol(underlying)
        ib = self._require_connection()
        try:
            from ib_insync import Stock  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("ib_insync is required for IBKRLiveFeed") from exc

        # Get the underlying contract id needed by reqSecDefOptParams
        underlying_contract = Stock(sym, "SMART", "USD")
        await ib.qualifyContractsAsync(underlying_contract)
        params_list = await ib.reqSecDefOptParamsAsync(
            underlying_contract.symbol, "", "STK", underlying_contract.conId
        )
        if not params_list:
            return ChainSnapshot(
                underlying=sym, expiry=expiry, snapshot_time=datetime.now(tz=UTC),
                contracts=[],
            )

        # Pick the SMART exchange entry for OPRA
        params = next((p for p in params_list if p.exchange == "SMART"), params_list[0])

        # Filter strikes to the requested expiry
        expiry_str = expiry.strftime("%Y%m%d")
        if expiry_str not in params.expirations:
            logger.warning("expiry %s not in chain for %s", expiry_str, sym)
            return ChainSnapshot(
                underlying=sym, expiry=expiry, snapshot_time=datetime.now(tz=UTC),
                contracts=[],
            )

        # Find current underlying price to pick ATM strikes
        ticker = ib.reqMktData(underlying_contract, "", True, False)
        for _ in range(10):
            await asyncio.sleep(0.2)
            if ticker.last is not None and not str(ticker.last).lower() == "nan":
                break
        last_price = _to_decimal(ticker.last) or _to_decimal(ticker.marketPrice()) \
            or Decimal("0")
        ib.cancelMktData(underlying_contract)

        if last_price <= 0:
            logger.warning("no valid underlying price for %s; chain empty", sym)
            return ChainSnapshot(
                underlying=sym, expiry=expiry, snapshot_time=datetime.now(tz=UTC),
                contracts=[],
            )

        # Pick the 5 strikes nearest last_price (ATM ±2)
        sorted_strikes = sorted(
            params.strikes, key=lambda s: abs(Decimal(str(s)) - last_price)
        )[:5]

        contracts: list[OptionContract] = []
        for strike_f in sorted_strikes:
            strike = Decimal(str(strike_f))
            for right in ("C", "P"):
                contracts.append(OptionContract(
                    underlying=sym, expiry=expiry, strike=strike, right=right,
                ))

        return ChainSnapshot(
            underlying=sym, expiry=expiry, snapshot_time=datetime.now(tz=UTC),
            contracts=contracts,
        )

    async def stream_option_quotes(
        self, contracts: list[OptionContract]
    ) -> AsyncIterator[OptionQuote]:
        if not contracts:
            return
        ib = self._require_connection()
        try:
            from ib_insync import Option  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("ib_insync is required for IBKRLiveFeed") from exc

        ib_contracts = [
            Option(
                c.underlying, c.expiry.strftime("%Y%m%d"), float(c.strike),
                c.right, "SMART", multiplier=str(c.multiplier),
            )
            for c in contracts
        ]
        await ib.qualifyContractsAsync(*ib_contracts)
        # Generic ticks 106 = Option Implied Volatility + Greeks
        tickers = [
            ib.reqMktData(ic, self.GENERIC_TICK_GREEKS, False, False)
            for ic in ib_contracts
        ]
        try:
            while True:
                await ib.updateEvent
                for c, ticker in zip(contracts, tickers, strict=True):
                    bid = _to_decimal(ticker.bid)
                    ask = _to_decimal(ticker.ask)
                    if bid is None or ask is None:
                        continue
                    greeks = (
                        ticker.modelGreeks
                        or ticker.lastGreeks
                        or ticker.bidGreeks
                        or ticker.askGreeks
                    )
                    yield OptionQuote(
                        underlying=c.underlying,
                        expiry=c.expiry,
                        strike=c.strike,
                        right=c.right,
                        timestamp=datetime.now(tz=UTC),
                        bid=bid,
                        ask=ask,
                        last=_to_decimal(ticker.last),
                        iv=_to_decimal(greeks.impliedVol) if greeks else None,
                        delta=_to_decimal(greeks.delta) if greeks else None,
                        gamma=_to_decimal(greeks.gamma) if greeks else None,
                        theta=_to_decimal(greeks.theta) if greeks else None,
                        vega=_to_decimal(greeks.vega) if greeks else None,
                    )
        finally:
            for ic in ib_contracts:
                try:
                    ib.cancelMktData(ic)
                except Exception:
                    pass
