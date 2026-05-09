"""Factory: build a ``MarketDataFeed`` from a ``DataConfig``."""

from __future__ import annotations

from config.schema import DataConfig
from contracts.data_feed import MarketDataFeed

from engine.data_feeds.ibkr_delayed import IBKRDelayedFeed
from engine.data_feeds.ibkr_live import IBKRLiveFeed
from engine.data_feeds.replay import ReplayFeed
from engine.data_feeds.synthetic_options import SyntheticOptionsFeed


def _make_yfinance_feed() -> MarketDataFeed:
    # yfinance + pandas live in the [dev] extra so they're not in prod images.
    # Importing here keeps factory.py importable in production where the
    # configured feed is ibkr_live and yfinance was never installed.
    from engine.data_feeds.yfinance import YFinanceFeed

    return YFinanceFeed()


def make_feed(config: DataConfig) -> MarketDataFeed:
    """Construct the equity feed selected by ``config.feed``."""
    feed = config.feed
    if feed == "yfinance":
        return _make_yfinance_feed()
    if feed == "ibkr_delayed":
        return IBKRDelayedFeed()
    if feed == "replay":
        if config.replay_path is None:
            raise ValueError("data.replay_path is required when feed == 'replay'")
        return ReplayFeed(config.replay_path)
    if feed == "synthetic_options":
        return SyntheticOptionsFeed(_make_yfinance_feed())
    if feed == "ibkr_live":
        return IBKRLiveFeed()
    raise ValueError(f"unknown feed: {feed!r}")  # pragma: no cover - Literal exhaustive


def make_options_feed(
    config: DataConfig, equity_feed: MarketDataFeed
) -> MarketDataFeed:
    """Construct the options feed selected by ``config.options_feed``.

    The returned feed wraps ``equity_feed`` for underlying price discovery.
    """
    options_feed = config.options_feed
    if options_feed == "synthetic":
        return SyntheticOptionsFeed(equity_feed)
    if options_feed == "ibkr_live":
        # If the equity feed is already IBKRLiveFeed, reuse it so we share
        # one IB connection (avoids "duplicate clientId" errors).
        if isinstance(equity_feed, IBKRLiveFeed):
            return equity_feed
        return IBKRLiveFeed()
    raise ValueError(  # pragma: no cover - Literal exhaustive
        f"unknown options_feed: {options_feed!r}"
    )
