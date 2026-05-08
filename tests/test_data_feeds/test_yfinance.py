"""Unit tests for engine.data_feeds.yfinance — fully monkeypatched, no network."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pandas as pd
import pytest
from contracts.data_feed import Bar, OptionContract, Quote
from engine.data_feeds.yfinance import YFinanceFeed


def _fake_bars_df() -> pd.DataFrame:
    idx = [
        datetime(2026, 4, 15, 13, 30, tzinfo=UTC),
        datetime(2026, 4, 15, 13, 31, tzinfo=UTC),
        datetime(2026, 4, 15, 13, 32, tzinfo=UTC),
    ]
    return pd.DataFrame(
        {
            "Open": [450.0, 450.5, 451.0],
            "High": [450.7, 451.2, 451.5],
            "Low": [449.8, 450.3, 450.9],
            "Close": [450.5, 451.0, 451.2],
            "Volume": [1000, 1100, 1050],
        },
        index=idx,
    )


async def test_stream_equity_bars_well_formed(monkeypatch: pytest.MonkeyPatch) -> None:
    feed = YFinanceFeed()

    def fake_fetch(self: YFinanceFeed, symbol: str) -> Any:
        return _fake_bars_df()

    monkeypatch.setattr(YFinanceFeed, "_fetch_bars", fake_fetch, raising=True)

    bars: list[Bar] = []
    async for b in feed.stream_equity_bars("QQQ"):
        bars.append(b)
    assert len(bars) == 3
    for b in bars:
        assert b.symbol == "QQQ"
        assert b.interval_seconds == 60
        assert isinstance(b.open, Decimal)
        assert isinstance(b.close, Decimal)
        assert b.high >= b.low
    assert bars[0].close == Decimal("450.5")
    assert bars[1].close == Decimal("451.0")


async def test_stream_equity_bars_empty_dataframe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feed = YFinanceFeed()

    monkeypatch.setattr(
        YFinanceFeed,
        "_fetch_bars",
        lambda self, symbol: pd.DataFrame(),
        raising=True,
    )
    bars = [b async for b in feed.stream_equity_bars("QQQ")]
    assert bars == []


async def test_stream_equity_bars_handles_naive_timestamps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feed = YFinanceFeed()

    idx = [datetime(2026, 4, 15, 13, 30)]  # naive
    df = pd.DataFrame(
        {
            "Open": [1.0],
            "High": [1.1],
            "Low": [0.9],
            "Close": [1.05],
            "Volume": [10],
        },
        index=idx,
    )
    monkeypatch.setattr(
        YFinanceFeed, "_fetch_bars", lambda self, symbol: df, raising=True
    )
    bars = [b async for b in feed.stream_equity_bars("QQQ")]
    assert bars[0].open_time.tzinfo is not None


async def test_stream_equity_quotes_with_bid_ask(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feed = YFinanceFeed()
    monkeypatch.setattr(
        YFinanceFeed,
        "_fetch_fast_info",
        lambda self, symbol: {"bid": 450.10, "ask": 450.20, "last_price": 450.15},
        raising=True,
    )
    quotes: list[Quote] = []
    async for q in feed.stream_equity_quotes("QQQ"):
        quotes.append(q)
    assert len(quotes) == 1
    assert quotes[0].bid == Decimal("450.10")
    assert quotes[0].ask == Decimal("450.20")
    assert quotes[0].last == Decimal("450.15")


async def test_stream_equity_quotes_falls_back_to_last(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feed = YFinanceFeed()
    monkeypatch.setattr(
        YFinanceFeed,
        "_fetch_fast_info",
        lambda self, symbol: {"last_price": 450.15},
        raising=True,
    )
    quotes = [q async for q in feed.stream_equity_quotes("QQQ")]
    assert len(quotes) == 1
    assert quotes[0].bid == quotes[0].ask == Decimal("450.15")


async def test_stream_equity_quotes_no_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feed = YFinanceFeed()
    monkeypatch.setattr(
        YFinanceFeed, "_fetch_fast_info", lambda self, symbol: {}, raising=True
    )
    quotes = [q async for q in feed.stream_equity_quotes("QQQ")]
    assert quotes == []


async def test_get_option_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    feed = YFinanceFeed()
    calls = pd.DataFrame({"strike": [445.0, 450.0, 455.0]})
    puts = pd.DataFrame({"strike": [445.0, 450.0]})
    monkeypatch.setattr(
        YFinanceFeed,
        "_fetch_option_chain",
        lambda self, symbol, expiry_iso: (calls, puts),
        raising=True,
    )
    snap = await feed.get_option_chain("QQQ", date(2026, 4, 16))
    assert snap.underlying == "QQQ"
    assert len(snap.contracts) == 5
    rights = [c.right for c in snap.contracts]
    assert rights.count("C") == 3
    assert rights.count("P") == 2
    for c in snap.contracts:
        assert isinstance(c, OptionContract)
        assert c.expiry == date(2026, 4, 16)


async def test_get_option_chain_handles_fetch_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feed = YFinanceFeed()

    def boom(self: YFinanceFeed, symbol: str, expiry_iso: str) -> Any:
        raise RuntimeError("network down")

    monkeypatch.setattr(YFinanceFeed, "_fetch_option_chain", boom, raising=True)
    snap = await feed.get_option_chain("QQQ", date(2026, 4, 16))
    assert snap.contracts == []


async def test_stream_option_quotes_raises() -> None:
    feed = YFinanceFeed()
    with pytest.raises(NotImplementedError):
        async for _ in feed.stream_option_quotes([]):
            pass
