"""Unit tests for engine.indicators.vwap."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from contracts.data_feed import Bar
from engine.indicators.vwap import session_vwap


def _bar(
    high: str,
    low: str,
    close: str,
    volume: int,
    minute: int = 0,
    open_: str | None = None,
) -> Bar:
    return Bar(
        symbol="TEST",
        interval_seconds=60,
        open_time=datetime(2026, 4, 15, 13, 30 + minute, tzinfo=UTC),
        open=Decimal(open_ if open_ is not None else close),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=volume,
    )


def test_empty_input_returns_none() -> None:
    assert session_vwap([]) is None


def test_single_bar_vwap_equals_typical_price() -> None:
    bar = _bar(high="11", low="9", close="10", volume=100)
    expected = (Decimal("11") + Decimal("9") + Decimal("10")) / Decimal(3)
    assert session_vwap([bar]) == expected


def test_two_bars_volume_weighted() -> None:
    b1 = _bar(high="12", low="10", close="11", volume=100, minute=0)
    b2 = _bar(high="14", low="12", close="13", volume=300, minute=1)
    typical1 = (Decimal("12") + Decimal("10") + Decimal("11")) / Decimal(3)
    typical2 = (Decimal("14") + Decimal("12") + Decimal("13")) / Decimal(3)
    expected = (typical1 * Decimal(100) + typical2 * Decimal(300)) / Decimal(400)
    assert session_vwap([b1, b2]) == expected


def test_zero_total_volume_returns_none() -> None:
    b1 = _bar(high="11", low="9", close="10", volume=0, minute=0)
    b2 = _bar(high="11", low="9", close="10", volume=0, minute=1)
    assert session_vwap([b1, b2]) is None


def test_returns_decimal_type() -> None:
    bar = _bar(high="11", low="9", close="10", volume=50)
    result = session_vwap([bar])
    assert isinstance(result, Decimal)


def test_negative_volume_raises() -> None:
    # Pydantic Bar model accepts negative ints for volume since it's typed as int;
    # we need to bypass field validation for the test, so build via model_construct.
    bad = Bar.model_construct(
        symbol="TEST",
        interval_seconds=60,
        open_time=datetime(2026, 4, 15, 13, 30, tzinfo=UTC),
        open=Decimal("10"),
        high=Decimal("11"),
        low=Decimal("9"),
        close=Decimal("10"),
        volume=-1,
        vwap=None,
    )
    with pytest.raises(ValueError):
        session_vwap([bad])
