"""Yahoo Finance market data feed (delayed; equity only)."""

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


def _to_decimal(value: Any) -> Decimal:
    """Convert a numeric to Decimal via str() to avoid float artifacts."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class YFinanceFeed(BaseFeed):
    """Yahoo Finance feed.

    Equity bars/quotes are sourced from yfinance; option chains use
    yfinance's ``Ticker.option_chain``. Real-time option quote streaming
    is NOT supported — pair with :class:`SyntheticOptionsFeed`.
    """

    name: str = "yfinance"

    def __init__(self, period: str = "1d", interval: str = "1m") -> None:
        self._period = period
        self._interval = interval

    # -- internal helpers ----------------------------------------------------

    def _fetch_bars(self, symbol: str) -> Any:
        """Fetch a DataFrame of intraday bars for ``symbol``.

        Tests monkeypatch this method; it is the only network entry point
        used by ``stream_equity_bars``.
        """
        import yfinance as yf

        return yf.download(
            symbol,
            period=self._period,
            interval=self._interval,
            progress=False,
            auto_adjust=False,
        )

    def _fetch_fast_info(self, symbol: str) -> dict[str, Any]:
        """Return a dict of fast_info fields for ``symbol``.

        Tests monkeypatch this method.
        """
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        info = getattr(ticker, "fast_info", {})
        # ``fast_info`` is a mapping-like object; coerce to plain dict.
        try:
            return dict(info)
        except Exception:  # pragma: no cover - defensive only
            return {}

    def _fetch_option_chain(self, symbol: str, expiry_iso: str) -> tuple[Any, Any]:
        """Fetch a yfinance option chain for ``symbol`` on ``expiry_iso``."""
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        chain = ticker.option_chain(expiry_iso)
        return chain.calls, chain.puts

    # -- public API ----------------------------------------------------------

    async def stream_equity_bars(
        self, symbol: str, interval_seconds: int = 60
    ) -> AsyncIterator[Bar]:
        sym = self._validate_symbol(symbol)
        df = self._fetch_bars(sym)
        if df is None or len(df) == 0:
            return
        # yfinance can return a MultiIndex columns DataFrame when a single
        # symbol is downloaded with newer versions. Normalize:
        try:
            import pandas as pd  # type: ignore

            if hasattr(df, "columns") and isinstance(df.columns, pd.MultiIndex):
                df = df.droplevel(1, axis=1)
        except Exception:  # pragma: no cover - if pandas missing
            pass

        for ts, row in df.iterrows():
            try:
                open_time: datetime
                if isinstance(ts, datetime):
                    open_time = ts
                else:  # pragma: no cover - pandas Timestamp duck-types
                    open_time = ts.to_pydatetime()  # type: ignore[union-attr]
                if open_time.tzinfo is None:
                    open_time = open_time.replace(tzinfo=UTC)
                yield Bar(
                    symbol=sym,
                    interval_seconds=interval_seconds,
                    open_time=open_time,
                    open=_to_decimal(row["Open"]),
                    high=_to_decimal(row["High"]),
                    low=_to_decimal(row["Low"]),
                    close=_to_decimal(row["Close"]),
                    volume=int(row["Volume"]),
                )
            except Exception as exc:  # pragma: no cover - skip malformed row
                logger.warning("yfinance: skipping malformed row for %s: %s", sym, exc)
                continue

    async def stream_equity_quotes(self, symbol: str) -> AsyncIterator[Quote]:
        sym = self._validate_symbol(symbol)
        info = self._fetch_fast_info(sym)
        bid = info.get("bid")
        ask = info.get("ask")
        last = info.get("last_price") or info.get("lastPrice") or info.get("last")
        ts = datetime.now(tz=UTC)
        if bid is not None and ask is not None and float(bid) > 0 and float(ask) > 0:
            yield Quote(
                symbol=sym,
                timestamp=ts,
                bid=_to_decimal(bid),
                ask=_to_decimal(ask),
                last=_to_decimal(last) if last is not None else None,
            )
            return
        # Fallback: use last as both bid and ask (delayed snapshot)
        if last is None:
            return
        mid = _to_decimal(last)
        yield Quote(symbol=sym, timestamp=ts, bid=mid, ask=mid, last=mid)

    async def get_option_chain(self, underlying: str, expiry: date) -> ChainSnapshot:
        sym = self._validate_symbol(underlying)
        snapshot_time = datetime.now(tz=UTC)
        contracts: list[OptionContract] = []
        try:
            calls, puts = self._fetch_option_chain(sym, expiry.isoformat())
        except Exception as exc:
            logger.warning(
                "yfinance: failed to fetch option chain for %s @ %s: %s",
                sym,
                expiry,
                exc,
            )
            return ChainSnapshot(
                underlying=sym, expiry=expiry, snapshot_time=snapshot_time, contracts=[]
            )

        for df, right in ((calls, "C"), (puts, "P")):
            if df is None or len(df) == 0:
                continue
            for _, row in df.iterrows():
                try:
                    contracts.append(
                        OptionContract(
                            underlying=sym,
                            expiry=expiry,
                            strike=_to_decimal(row["strike"]),
                            right=right,  # type: ignore[arg-type]
                        )
                    )
                except Exception as exc:  # pragma: no cover
                    logger.warning("yfinance: skipping malformed contract row: %s", exc)
                    continue
        return ChainSnapshot(
            underlying=sym,
            expiry=expiry,
            snapshot_time=snapshot_time,
            contracts=contracts,
        )

    async def stream_option_quotes(
        self, contracts: list[OptionContract]
    ) -> AsyncIterator[OptionQuote]:
        raise NotImplementedError(
            "YFinanceFeed has no real-time option quotes — pair with SyntheticOptionsFeed"
        )
        if False:  # pragma: no cover - make this an async generator for typing
            yield  # type: ignore[unreachable]
