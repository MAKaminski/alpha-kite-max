"""Unit tests for engine.data_feeds.factory."""

from __future__ import annotations

from pathlib import Path

import pytest
from config.schema import DataConfig
from engine.data_feeds.factory import make_feed, make_options_feed
from engine.data_feeds.ibkr_delayed import IBKRDelayedFeed
from engine.data_feeds.replay import ReplayFeed
from engine.data_feeds.synthetic_options import SyntheticOptionsFeed
from engine.data_feeds.yfinance import YFinanceFeed

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "qqq_2026-04-15_1min.json"
)


def test_make_feed_yfinance() -> None:
    feed = make_feed(DataConfig(feed="yfinance"))
    assert isinstance(feed, YFinanceFeed)


def test_make_feed_ibkr_delayed() -> None:
    feed = make_feed(DataConfig(feed="ibkr_delayed"))
    assert isinstance(feed, IBKRDelayedFeed)


def test_make_feed_replay() -> None:
    feed = make_feed(DataConfig(feed="replay", replay_path=str(FIXTURE)))
    assert isinstance(feed, ReplayFeed)


def test_make_feed_replay_without_path_raises() -> None:
    with pytest.raises(ValueError):
        make_feed(DataConfig(feed="replay"))


def test_make_feed_synthetic_options() -> None:
    feed = make_feed(DataConfig(feed="synthetic_options"))
    assert isinstance(feed, SyntheticOptionsFeed)


def test_make_feed_ibkr_live_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        make_feed(DataConfig(feed="ibkr_live"))


def test_make_options_feed_synthetic() -> None:
    equity = YFinanceFeed()
    options = make_options_feed(DataConfig(options_feed="synthetic"), equity)
    assert isinstance(options, SyntheticOptionsFeed)


def test_make_options_feed_ibkr_live_raises() -> None:
    equity = YFinanceFeed()
    with pytest.raises(NotImplementedError):
        make_options_feed(DataConfig(options_feed="ibkr_live"), equity)
