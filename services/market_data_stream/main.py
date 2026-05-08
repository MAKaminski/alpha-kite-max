"""Market data stream service.

Reads ticks/bars from the configured feed and writes them to persistence.
Runs as a separate process from the strategy engine so a slow feed never
blocks order placement.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal as posix_signal
import sys
from pathlib import Path

from config.schema import StrategyConfig, load_config
from engine.data_feeds.factory import make_feed

from services.persistence.storage import InMemoryBackend, StorageBackend, SupabaseBackend
from services.persistence.writer import PersistenceWriter

LOG = logging.getLogger("alpha_kite.market_data_stream")


def _build_storage() -> StorageBackend:
    if os.getenv("SUPABASE_DB_URL"):
        return SupabaseBackend(os.environ["SUPABASE_DB_URL"])
    LOG.warning("SUPABASE_DB_URL unset; using in-memory persistence")
    return InMemoryBackend()


async def run(cfg: StrategyConfig) -> None:
    LOG.info("starting market-data stream; feed=%s symbol=%s",
             cfg.data.feed, cfg.universe.symbol)
    feed = make_feed(cfg.data)
    writer = PersistenceWriter(_build_storage())

    stop_event = asyncio.Event()

    def _on_signal(_signo, _frame):  # type: ignore[no-untyped-def]
        LOG.info("shutdown signal received")
        stop_event.set()

    posix_signal.signal(posix_signal.SIGINT, _on_signal)
    posix_signal.signal(posix_signal.SIGTERM, _on_signal)

    async def _drain_bars() -> None:
        async for bar in feed.stream_equity_bars(
            cfg.universe.symbol, cfg.data.bar_interval_seconds
        ):
            if stop_event.is_set():
                return
            await writer.write_bar(bar, feed=cfg.data.feed)

    async def _drain_quotes() -> None:
        async for quote in feed.stream_equity_quotes(cfg.universe.symbol):
            if stop_event.is_set():
                return
            await writer.write_tick(quote, feed=cfg.data.feed)

    await asyncio.gather(_drain_bars(), _drain_quotes(), return_exceptions=True)
    LOG.info("market-data stream stopped")


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    cfg_path = os.getenv("STRATEGY_CONFIG", "./config/strategy.yaml")
    if not Path(cfg_path).exists():
        LOG.error("config not found: %s", cfg_path)
        sys.exit(2)
    cfg = load_config(cfg_path)
    asyncio.run(run(cfg))


if __name__ == "__main__":  # pragma: no cover
    main()
