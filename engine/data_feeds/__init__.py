"""Market data feed implementations.

Each module in this package provides a concrete `MarketDataFeed`
implementation. Use `engine.data_feeds.factory.make_feed` to construct
the feed configured by `config.data`.
"""

from __future__ import annotations

from engine.data_feeds.base import BaseFeed
from engine.data_feeds.factory import make_feed, make_options_feed
from engine.data_feeds.ibkr_delayed import IBKRDelayedFeed
from engine.data_feeds.replay import ReplayFeed
from engine.data_feeds.synthetic_options import SyntheticOptionsFeed
from engine.data_feeds.yfinance import YFinanceFeed

__all__ = [
    "BaseFeed",
    "IBKRDelayedFeed",
    "ReplayFeed",
    "SyntheticOptionsFeed",
    "YFinanceFeed",
    "make_feed",
    "make_options_feed",
]
