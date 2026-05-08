"""Unit tests for engine.data_feeds.replay."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from contracts.data_feed import Bar, Quote
from engine.data_feeds.replay import ReplayFeed

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "qqq_2026-04-15_1min.json"


def _expected_bars() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["bars"]


async def test_replay_yields_all_bars_in_order() -> None:
    feed = ReplayFeed(FIXTURE)
    bars: list[Bar] = []
    async for bar in feed.stream_equity_bars("QQQ"):
        bars.append(bar)
    expected = _expected_bars()
    assert len(bars) == len(expected) == 60


async def test_replay_bars_have_monotonic_timestamps() -> None:
    feed = ReplayFeed(FIXTURE)
    timestamps = [b.open_time async for b in feed.stream_equity_bars("QQQ")]
    assert timestamps == sorted(timestamps)
    # Strictly monotonic too.
    for prev, nxt in zip(timestamps, timestamps[1:]):
        assert nxt > prev


async def test_replay_close_values_match_fixture() -> None:
    feed = ReplayFeed(FIXTURE)
    expected = [Decimal(b["close"]) for b in _expected_bars()]
    actual = [bar.close async for bar in feed.stream_equity_bars("QQQ")]
    assert actual == expected


async def test_replay_quotes_synthesized_around_close() -> None:
    feed = ReplayFeed(FIXTURE)
    spread = Decimal("0.01")
    quotes: list[Quote] = []
    async for q in feed.stream_equity_quotes("QQQ"):
        quotes.append(q)
    assert len(quotes) == 60
    closes = [Decimal(b["close"]) for b in _expected_bars()]
    for q, c in zip(quotes, closes):
        assert q.last == c
        assert q.bid == c - spread
        assert q.ask == c + spread


async def test_replay_rejects_unknown_symbol() -> None:
    feed = ReplayFeed(FIXTURE)
    with pytest.raises(ValueError):
        async for _ in feed.stream_equity_bars("AAPL"):
            pass


async def test_replay_validates_empty_symbol() -> None:
    feed = ReplayFeed(FIXTURE)
    with pytest.raises(ValueError):
        async for _ in feed.stream_equity_bars(""):
            pass


def test_replay_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        ReplayFeed("/tmp/does-not-exist.json")


def test_replay_negative_speed_raises() -> None:
    with pytest.raises(ValueError):
        ReplayFeed(FIXTURE, speed=-1.0)


async def test_replay_get_option_chain_is_empty() -> None:
    feed = ReplayFeed(FIXTURE)
    snap = await feed.get_option_chain("QQQ", date(2026, 4, 15))
    assert snap.contracts == []
    assert snap.underlying == "QQQ"


async def test_replay_stream_option_quotes_raises() -> None:
    feed = ReplayFeed(FIXTURE)
    with pytest.raises(NotImplementedError):
        async for _ in feed.stream_option_quotes([]):
            pass
