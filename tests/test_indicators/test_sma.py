"""Unit tests for engine.indicators.sma."""

from __future__ import annotations

from decimal import Decimal

import pytest
from engine.indicators.sma import simple_moving_average


def _d(values: list[str]) -> list[Decimal]:
    return [Decimal(v) for v in values]


def test_returns_none_when_under_period() -> None:
    assert simple_moving_average(_d(["1", "2", "3"]), period=4) is None


def test_returns_none_on_empty_input() -> None:
    assert simple_moving_average([], period=3) is None


def test_exact_period_average() -> None:
    result = simple_moving_average(_d(["1", "2", "3"]), period=3)
    assert result == Decimal("2")


def test_uses_trailing_window() -> None:
    closes = _d(["10", "20", "30", "40", "50"])
    # SMA9 with only 5 points → None; SMA3 over last 3 → (30+40+50)/3 = 40
    assert simple_moving_average(closes, period=3) == Decimal("40")


def test_decimal_precision_preserved() -> None:
    closes = _d(["1.1111", "2.2222", "3.3333"])
    expected = (Decimal("1.1111") + Decimal("2.2222") + Decimal("3.3333")) / Decimal(3)
    assert simple_moving_average(closes, period=3) == expected


def test_zero_period_raises() -> None:
    with pytest.raises(ValueError):
        simple_moving_average(_d(["1", "2"]), period=0)


def test_negative_period_raises() -> None:
    with pytest.raises(ValueError):
        simple_moving_average(_d(["1", "2"]), period=-1)


def test_single_element_window() -> None:
    closes = _d(["7.5"])
    assert simple_moving_average(closes, period=1) == Decimal("7.5")


def test_does_not_use_floats() -> None:
    closes = _d(["0.1", "0.2"])
    result = simple_moving_average(closes, period=2)
    assert isinstance(result, Decimal)
    # Float arithmetic would give 0.15000000000000002; Decimal is exact.
    assert result == Decimal("0.15")
