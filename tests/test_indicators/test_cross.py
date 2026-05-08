"""Unit and golden tests for engine.indicators.cross plus full-pipeline coverage."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from contracts.data_feed import Bar
from engine.indicators.cross import cross_events, detect_cross
from engine.indicators.sma import simple_moving_average
from engine.indicators.vwap import session_vwap

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "qqq_2026-04-15_1min.json"


# ---------------------------------------------------------------------------
# detect_cross unit tests
# ---------------------------------------------------------------------------


def test_first_call_returns_none_when_prev_missing() -> None:
    assert detect_cross(None, None, Decimal("1"), Decimal("2")) == "NONE"
    assert detect_cross(None, Decimal("1"), Decimal("2"), Decimal("1")) == "NONE"
    assert detect_cross(Decimal("1"), None, Decimal("2"), Decimal("1")) == "NONE"


def test_up_cross_when_strictly_above() -> None:
    assert detect_cross(Decimal("1"), Decimal("2"), Decimal("3"), Decimal("2.5")) == "UP"


def test_down_cross_when_strictly_below() -> None:
    assert detect_cross(Decimal("3"), Decimal("2"), Decimal("1"), Decimal("2")) == "DOWN"


def test_equal_then_above_counts_as_up() -> None:
    # prev_a == prev_b, then a moves above → UP
    assert detect_cross(Decimal("2"), Decimal("2"), Decimal("3"), Decimal("2")) == "UP"


def test_equal_then_below_counts_as_down() -> None:
    assert detect_cross(Decimal("2"), Decimal("2"), Decimal("1"), Decimal("2")) == "DOWN"


def test_no_change_returns_none() -> None:
    assert detect_cross(Decimal("3"), Decimal("2"), Decimal("4"), Decimal("2")) == "NONE"
    assert detect_cross(Decimal("1"), Decimal("2"), Decimal("1"), Decimal("3")) == "NONE"


def test_touching_but_not_crossing_returns_none() -> None:
    # a was above, now a equals b — not strictly below → NONE
    assert detect_cross(Decimal("3"), Decimal("2"), Decimal("2"), Decimal("2")) == "NONE"
    # a was below, now a equals b — not strictly above → NONE
    assert detect_cross(Decimal("1"), Decimal("2"), Decimal("2"), Decimal("2")) == "NONE"


# ---------------------------------------------------------------------------
# cross_events unit tests
# ---------------------------------------------------------------------------


def test_cross_events_length_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        cross_events([Decimal("1")], [Decimal("1"), Decimal("2")])


def test_cross_events_empty_returns_empty() -> None:
    assert cross_events([], []) == []


def test_cross_events_skips_leading_nones() -> None:
    a: list[Decimal | None] = [None, None, Decimal("1"), Decimal("3")]
    b: list[Decimal | None] = [None, None, Decimal("2"), Decimal("2")]
    # First Decimal pair (idx 2) primes prev; idx 3 sees prev_a<=prev_b and curr_a>curr_b → UP
    assert cross_events(a, b) == [(3, "UP")]


def test_cross_events_simple_up_then_down() -> None:
    a = [Decimal(v) for v in ("1", "2", "3", "2", "1")]
    b = [Decimal(v) for v in ("2", "2", "2", "2", "2")]
    # idx 0: prev None → NONE
    # idx 1: prev (1,2), curr (2,2): 1<=2 and 2>2? no → NONE
    # idx 2: prev (2,2), curr (3,2): 2<=2 and 3>2 → UP
    # idx 3: prev (3,2), curr (2,2): 3>=2 and 2<2? no → NONE
    # idx 4: prev (2,2), curr (1,2): 2>=2 and 1<2 → DOWN
    assert cross_events(a, b) == [(2, "UP"), (4, "DOWN")]


# ---------------------------------------------------------------------------
# Golden test: load fixture and run full SMA9 + VWAP + cross pipeline
# ---------------------------------------------------------------------------


def _load_fixture_bars() -> list[Bar]:
    raw = json.loads(FIXTURE.read_text())
    bars: list[Bar] = []
    for entry in raw["bars"]:
        bars.append(
            Bar(
                symbol=entry["symbol"],
                interval_seconds=entry["interval_seconds"],
                open_time=datetime.fromisoformat(entry["open_time"]),
                open=Decimal(entry["open"]),
                high=Decimal(entry["high"]),
                low=Decimal(entry["low"]),
                close=Decimal(entry["close"]),
                volume=entry["volume"],
                vwap=Decimal(entry["vwap"]) if entry.get("vwap") is not None else None,
            )
        )
    return bars


def _compute_series(bars: list[Bar]) -> tuple[list[Decimal | None], list[Decimal | None]]:
    sma9_series: list[Decimal | None] = []
    vwap_series: list[Decimal | None] = []
    closes: list[Decimal] = []
    for i, bar in enumerate(bars, start=1):
        closes.append(bar.close)
        sma9_series.append(simple_moving_average(closes, period=9))
        vwap_series.append(session_vwap(bars[:i]))
    return sma9_series, vwap_series


def test_golden_fixture_loads_60_bars() -> None:
    bars = _load_fixture_bars()
    assert len(bars) == 60


def test_golden_sma9_warmup() -> None:
    bars = _load_fixture_bars()
    sma9_series, _ = _compute_series(bars)
    # First 8 bars should produce None, bar 9 (index 8) onward should be Decimal.
    assert all(v is None for v in sma9_series[:8])
    assert all(isinstance(v, Decimal) for v in sma9_series[8:])


def test_golden_vwap_present_for_every_bar() -> None:
    bars = _load_fixture_bars()
    _, vwap_series = _compute_series(bars)
    assert all(isinstance(v, Decimal) for v in vwap_series)


def test_golden_cross_events_match_expected() -> None:
    bars = _load_fixture_bars()
    sma9_series, vwap_series = _compute_series(bars)
    events = cross_events(sma9_series, vwap_series)

    # Expected indices were computed once from this fixture and pinned here.
    # If the fixture changes, regenerate this list.
    expected = [(19, "UP"), (47, "DOWN")]
    assert events == expected


def test_golden_first_cross_index_has_priming_pair() -> None:
    """Sanity: the first reported cross must occur at an index where both
    series had a Decimal value at i-1 and i (prev primed)."""
    bars = _load_fixture_bars()
    sma9_series, vwap_series = _compute_series(bars)
    events = cross_events(sma9_series, vwap_series)
    assert events, "expected at least one cross in fixture"
    first_idx = events[0][0]
    assert sma9_series[first_idx] is not None
    assert sma9_series[first_idx - 1] is not None
    assert vwap_series[first_idx] is not None
    assert vwap_series[first_idx - 1] is not None
