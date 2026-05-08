"""Strategy engine orchestrator.

Wires the configured data feed into the strategy, runs every emitted
OrderIntent through the risk pipeline, hands the survivors to the broker,
and persists every event. The orchestrator is the single component that
combines all eight Wave 1 tracks at runtime.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal as posix_signal
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from config.schema import StrategyConfig, load_config
from contracts.broker import OrderIntent
from contracts.risk import RiskCheck
from contracts.strategy import (
    StrategyContext,
    StrategyDecision,
)
from engine.broker.dry_run import DryRunBroker
from engine.broker.ibkr_paper import IBKRPaperBroker
from engine.data_feeds.factory import make_feed, make_options_feed
from engine.risk.kill_switch import KillSwitchGuard
from engine.risk.limits import (
    DailyLossLimitGuard,
    MaxOpenPositionsGuard,
    MaxPremiumPctNavGuard,
)
from engine.risk.paper_guard import PaperAccountGuard
from engine.risk.pipeline import RiskPipeline
from engine.strategies.buy_vol_qqq_cross import BuyVolQQQCrossStrategy

from services.persistence.models import AuditEvent
from services.persistence.storage import InMemoryBackend, StorageBackend, SupabaseBackend
from services.persistence.writer import PersistenceWriter

LOG = logging.getLogger("alpha_kite.strategy_engine")


def _build_storage() -> StorageBackend:
    """Use Supabase if SUPABASE_DB_URL is set, otherwise in-memory (dry-run)."""
    if os.getenv("SUPABASE_DB_URL"):
        return SupabaseBackend(os.environ["SUPABASE_DB_URL"])
    LOG.warning("SUPABASE_DB_URL unset; using in-memory persistence (no durability)")
    return InMemoryBackend()


def _build_broker(cfg: StrategyConfig):
    """Return a BrokerGateway. v1 only allows paper mode; live raises at config load."""
    if cfg.broker.dry_run:
        LOG.info("broker.dry_run=true → using DryRunBroker (no orders placed)")
        return DryRunBroker()
    return IBKRPaperBroker(
        host=cfg.broker.host,
        port=cfg.broker.port,
        client_id=cfg.broker.client_id,
        dry_run=False,
        paper_account_allowlist=cfg.broker.paper_account_allowlist,
    )


def _build_risk_pipeline(cfg: StrategyConfig) -> RiskPipeline:
    return RiskPipeline(
        [
            KillSwitchGuard(cfg.risk.kill_switch_file),
            MaxOpenPositionsGuard(cfg.risk.max_open_positions),
            DailyLossLimitGuard(cfg.risk.daily_loss_limit_usd),
            MaxPremiumPctNavGuard(cfg.entry.max_premium_pct_nav),
            PaperAccountGuard(
                allowlist=cfg.broker.paper_account_allowlist,
                required_mode=cfg.broker.mode,
            ),
        ]
    )


async def _audit(
    writer: PersistenceWriter,
    actor: str,
    event_type: str,
    severity: str,
    message: str,
    payload: dict | None = None,
) -> None:
    await writer.write_audit(
        AuditEvent(
            ts=datetime.now(UTC),
            actor=actor,
            event_type=event_type,
            severity=severity,
            message=message,
            payload=payload or {},
        )
    )


async def run(cfg: StrategyConfig) -> None:
    """Main run loop. Blocks until SIGINT/SIGTERM or feed exhaustion."""
    LOG.info("starting strategy engine; feed=%s broker.mode=%s dry_run=%s",
             cfg.data.feed, cfg.broker.mode, cfg.broker.dry_run)

    storage = _build_storage()
    writer = PersistenceWriter(storage)

    equity_feed = make_feed(cfg.data)
    options_feed = make_options_feed(cfg.data, equity_feed)
    strategy = BuyVolQQQCrossStrategy(
        symbol=cfg.universe.symbol,
        sma_period=cfg.signal.params.sma_period,
        mode=cfg.entry.mode,
        contracts=cfg.entry.contracts,
        profit_target_pct=cfg.exit.profit_target_pct,
        stop_loss_pct=cfg.exit.stop_loss_pct,
        time_stop_minutes_before_close=cfg.exit.time_stop_minutes_before_close,
    )
    risk = _build_risk_pipeline(cfg)
    broker = _build_broker(cfg)
    await broker.connect()
    await _audit(writer, "engine", "STARTUP", "INFO",
                 f"engine started; feed={cfg.data.feed}", payload={
                     "feed": cfg.data.feed,
                     "broker_mode": cfg.broker.mode,
                     "dry_run": cfg.broker.dry_run,
                 })

    bar_history: list = []
    open_positions = 0
    realized_pnl_today = Decimal("0")

    stop_event = asyncio.Event()

    def _on_signal(_signo, _frame):  # type: ignore[no-untyped-def]
        LOG.info("shutdown signal received")
        stop_event.set()

    posix_signal.signal(posix_signal.SIGINT, _on_signal)
    posix_signal.signal(posix_signal.SIGTERM, _on_signal)

    # Background heartbeat so the /status page shows the engine alive even
    # outside market hours when the bar stream is silent.
    async def _heartbeat() -> None:
        while not stop_event.is_set():
            await _audit(writer, "engine", "HEARTBEAT", "INFO",
                         "engine alive",
                         payload={"feed": cfg.data.feed,
                                  "dry_run": cfg.broker.dry_run})
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=60)
            except TimeoutError:
                pass

    heartbeat_task = asyncio.create_task(_heartbeat())

    try:
        async for bar in equity_feed.stream_equity_bars(
            cfg.universe.symbol, cfg.data.bar_interval_seconds
        ):
            if stop_event.is_set():
                break

            await writer.write_bar(bar, feed=cfg.data.feed)
            bar_history.append(bar)
            account = await broker.get_account_summary()

            chain = await options_feed.get_option_chain(
                cfg.universe.symbol, bar.open_time.date()
            )
            quotes_iter = options_feed.stream_option_quotes(chain.contracts)
            option_quotes = []
            async for q in quotes_iter:
                option_quotes.append(q)
                if len(option_quotes) >= len(chain.contracts):
                    break

            ctx = StrategyContext(
                now=bar.open_time,
                last_bar=bar,
                bar_history=bar_history[-200:],
                option_quotes=option_quotes,
                open_positions=open_positions,
                cash_available=account.cash,
            )

            decision: StrategyDecision = strategy.on_bar(ctx)
            for sig in decision.signals:
                await writer.write_signal(sig)

            for intent in decision.intents:
                # Pick a representative premium for the risk check
                premium = _intent_premium(intent, option_quotes)
                check: RiskCheck = risk.evaluate(
                    intent=intent,
                    account=account,
                    open_positions=open_positions,
                    realized_pnl_today=realized_pnl_today,
                    last_premium=premium,
                )
                await writer.write_order_intent(intent, dry_run=cfg.broker.dry_run)
                if not check.allowed:
                    await _audit(writer, "risk", "RISK_BLOCK", "WARN",
                                 "intent blocked", payload={
                                     "intent_id": str(intent.intent_id),
                                     "reasons": check.reasons,
                                 })
                    continue

                update = await broker.place_order(intent)
                await _audit(writer, "broker", "ORDER_PLACED", "INFO",
                             f"placed {intent.side.value} {intent.symbol}",
                             payload={"intent_id": str(intent.intent_id),
                                      "status": update.status.value})
                if update.filled_qty > 0:
                    open_positions += 1 if intent.side.name == "BUY" else -1
                    open_positions = max(open_positions, 0)
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except (asyncio.CancelledError, Exception):
            pass
        await broker.disconnect()
        await _audit(writer, "engine", "SHUTDOWN", "INFO", "engine shut down")
        LOG.info("strategy engine stopped")


def _intent_premium(
    intent: OrderIntent, option_quotes: list
) -> Decimal:
    """Pick a representative premium for a risk check. Falls back to limit_price."""
    if intent.limit_price is not None:
        return intent.limit_price
    if intent.option is not None:
        for q in option_quotes:
            if (
                q.strike == intent.option.strike
                and q.right == intent.option.right
                and q.expiry == intent.option.expiry
            ):
                return q.mid
    return Decimal("0")


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
