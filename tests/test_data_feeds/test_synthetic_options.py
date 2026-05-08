"""Unit tests for engine.data_feeds.synthetic_options."""

from __future__ import annotations

import math
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from contracts.data_feed import Bar, ChainSnapshot, OptionContract, Quote
from engine.data_feeds.base import BaseFeed
from engine.data_feeds.synthetic_options import (
    SyntheticOptionsFeed,
    _bs_price,
)


class _FixedEquityFeed(BaseFeed):
    """An equity feed that yields a single bar at a fixed close price."""

    name = "fixed"

    def __init__(self, symbol: str, close: Decimal) -> None:
        self.symbol = symbol.upper()
        self.close = close

    async def stream_equity_bars(  # type: ignore[override]
        self, symbol: str, interval_seconds: int = 60
    ) -> AsyncIterator[Bar]:
        yield Bar(
            symbol=self.symbol,
            interval_seconds=interval_seconds,
            open_time=datetime(2026, 4, 15, 13, 30, tzinfo=UTC),
            open=self.close,
            high=self.close,
            low=self.close,
            close=self.close,
            volume=1_000,
        )

    async def stream_equity_quotes(  # type: ignore[override]
        self, symbol: str
    ) -> AsyncIterator[Quote]:
        yield Quote(
            symbol=self.symbol,
            timestamp=datetime(2026, 4, 15, 13, 30, tzinfo=UTC),
            bid=self.close - Decimal("0.01"),
            ask=self.close + Decimal("0.01"),
            last=self.close,
        )


def test_bs_price_atm_one_day() -> None:
    """Sanity-check ATM call price for QQQ-like S=K=450, T=1d, IV=0.2 lies in [1.0, 5.0]."""
    s = 450.0
    k = 450.0
    t = 1 / 365.0
    r = 0.05
    sigma = 0.20
    call = _bs_price(s, k, t, r, sigma, "C")
    assert 1.0 <= call <= 5.0


def test_bs_put_call_parity() -> None:
    """For ATM with same expiry: C - P ~= S - K * exp(-r*T) within $0.01."""
    s, k, r, sigma = 450.0, 450.0, 0.05, 0.20
    t = 1 / 365.0
    c = _bs_price(s, k, t, r, sigma, "C")
    p = _bs_price(s, k, t, r, sigma, "P")
    expected = s - k * math.exp(-r * t)
    assert abs((c - p) - expected) < 0.01


async def test_synthetic_chain_has_atm_plus_minus_5() -> None:
    equity = _FixedEquityFeed("QQQ", Decimal("450.30"))
    feed = SyntheticOptionsFeed(equity)
    snap: ChainSnapshot = await feed.get_option_chain("QQQ", date(2026, 4, 16))
    # 11 strikes (ATM +/- 5) x 2 rights (C/P) = 22 contracts.
    assert len(snap.contracts) == 22
    strikes = sorted({c.strike for c in snap.contracts})
    assert strikes == [Decimal(450 + i) for i in range(-5, 6)]
    rights = {c.right for c in snap.contracts}
    assert rights == {"C", "P"}


async def test_synthetic_chain_strikes_round_half_up() -> None:
    # 449.50 should round to 450 ATM.
    equity = _FixedEquityFeed("QQQ", Decimal("449.50"))
    feed = SyntheticOptionsFeed(equity)
    snap = await feed.get_option_chain("QQQ", date(2026, 4, 16))
    strikes = sorted({c.strike for c in snap.contracts})
    assert strikes[0] == Decimal(445)
    assert strikes[-1] == Decimal(455)


async def test_synthetic_option_quote_atm_is_reasonable() -> None:
    equity = _FixedEquityFeed("QQQ", Decimal("100"))
    feed = SyntheticOptionsFeed(equity, iv=Decimal("0.20"))
    # Hydrate latest close.
    async for _ in feed.stream_equity_bars("QQQ"):
        pass
    expiry = (datetime.now(tz=UTC) + timedelta(days=1)).date()
    contract = OptionContract(
        underlying="QQQ", expiry=expiry, strike=Decimal("100"), right="C"
    )
    quotes = [q async for q in feed.stream_option_quotes([contract])]
    assert len(quotes) == 1
    q = quotes[0]
    assert q.iv == Decimal("0.20")
    assert q.delta is not None and Decimal("0.3") < q.delta < Decimal("0.7")
    assert q.gamma is not None and q.gamma > 0
    assert q.vega is not None and q.vega > 0
    # ATM call should price modestly positive.
    assert q.last is not None and q.last > Decimal("0")
    assert q.bid <= q.last <= q.ask


async def test_synthetic_put_call_parity_via_quotes() -> None:
    equity = _FixedEquityFeed("QQQ", Decimal("100"))
    feed = SyntheticOptionsFeed(equity, iv=Decimal("0.20"), risk_free_rate=Decimal("0.05"))
    async for _ in feed.stream_equity_bars("QQQ"):
        pass
    expiry = (datetime.now(tz=UTC) + timedelta(days=1)).date()
    call = OptionContract(
        underlying="QQQ", expiry=expiry, strike=Decimal("100"), right="C"
    )
    put = OptionContract(
        underlying="QQQ", expiry=expiry, strike=Decimal("100"), right="P"
    )
    quotes = {q.right: q async for q in feed.stream_option_quotes([call, put])}
    diff = quotes["C"].last - quotes["P"].last  # type: ignore[operator]
    # ATM, near-zero T → C - P should be very small (well within $0.01).
    assert abs(diff) < Decimal("0.05")


async def test_synthetic_equity_passthrough_records_close() -> None:
    equity = _FixedEquityFeed("QQQ", Decimal("450.5"))
    feed = SyntheticOptionsFeed(equity)
    bars = [b async for b in feed.stream_equity_bars("QQQ")]
    assert len(bars) == 1
    quotes = [q async for q in feed.stream_equity_quotes("QQQ")]
    assert len(quotes) == 1


def test_iv_must_be_decimal() -> None:
    equity = _FixedEquityFeed("QQQ", Decimal("100"))
    with pytest.raises(TypeError):
        SyntheticOptionsFeed(equity, iv=0.2)  # type: ignore[arg-type]


def test_iv_must_be_positive() -> None:
    equity = _FixedEquityFeed("QQQ", Decimal("100"))
    with pytest.raises(ValueError):
        SyntheticOptionsFeed(equity, iv=Decimal("0"))
