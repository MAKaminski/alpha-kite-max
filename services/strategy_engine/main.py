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
from engine.strategies.buy_vol_qqq_cross_tick import BuyVolQQQCrossTickStrategy
from engine.strategies.sell_put_qqq_cross import (
    SellPutQQQCrossStrategy,
)
from engine.strategies.sell_put_qqq_cross import (
    TakeProfitTier as TickTakeProfitTier,
)

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


def _build_strategy(cfg: StrategyConfig):
    """Select strategy implementation based on signal.name in config."""
    if cfg.signal.name == "sell_put_qqq_cross":
        tiers_cfg = cfg.exit.tiers
        if tiers_cfg is None:
            # Use the strategy's built-in user-spec ladder.
            tier_objs = None
            stop_mult = None
        else:
            tier_objs = [
                TickTakeProfitTier(gain_pct=t.gain_pct, qty_fraction=t.qty_fraction)
                for t in tiers_cfg.take_profit_tiers
            ]
            stop_mult = tiers_cfg.stop_loss_multiple
        kwargs: dict = dict(
            symbol=cfg.universe.symbol,
            sma_window_seconds=cfg.signal.params.sma_window_seconds,
            cooldown_seconds=cfg.signal.params.cooldown_seconds,
            contracts=cfg.entry.contracts,
            time_stop_minutes_before_close=cfg.exit.time_stop_minutes_before_close,
            entry_delay_minutes_after_open=cfg.exit.entry_delay_minutes_after_open,
        )
        if tier_objs is not None:
            kwargs["take_profit_tiers"] = tier_objs
        if stop_mult is not None:
            kwargs["stop_loss_multiple"] = stop_mult
        return SellPutQQQCrossStrategy(**kwargs)
    if cfg.signal.name == "sma_vwap_cross_tick":
        return BuyVolQQQCrossTickStrategy(
            symbol=cfg.universe.symbol,
            sma_window_seconds=cfg.signal.params.sma_window_seconds,
            confirmation_seconds=cfg.signal.params.confirmation_seconds,
            mode=cfg.entry.mode,
            contracts=cfg.entry.contracts,
            profit_target_pct=cfg.exit.profit_target_pct,
            stop_loss_pct=cfg.exit.stop_loss_pct,
            time_stop_minutes_before_close=cfg.exit.time_stop_minutes_before_close,
            entry_delay_minutes_after_open=cfg.exit.entry_delay_minutes_after_open,
        )
    # default: bar strategy
    return BuyVolQQQCrossStrategy(
        symbol=cfg.universe.symbol,
        sma_period=cfg.signal.params.sma_period,
        mode=cfg.entry.mode,
        contracts=cfg.entry.contracts,
        profit_target_pct=cfg.exit.profit_target_pct,
        stop_loss_pct=cfg.exit.stop_loss_pct,
        time_stop_minutes_before_close=cfg.exit.time_stop_minutes_before_close,
        entry_delay_minutes_after_open=cfg.exit.entry_delay_minutes_after_open,
    )


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

    # Feed and broker share the same IB Gateway endpoint, but need different
    # clientIds when both are connected (broker uses cfg.broker.client_id).
    feed_client_id = cfg.broker.client_id + 1
    equity_feed = make_feed(
        cfg.data,
        ibkr_host=cfg.broker.host,
        ibkr_port=cfg.broker.port,
        ibkr_client_id=feed_client_id,
    )
    options_feed = make_options_feed(
        cfg.data,
        equity_feed,
        ibkr_host=cfg.broker.host,
        ibkr_port=cfg.broker.port,
        ibkr_client_id=feed_client_id,
    )
    strategy = _build_strategy(cfg)
    risk = _build_risk_pipeline(cfg)
    broker = _build_broker(cfg)
    await broker.connect()

    # Some feeds (IBKR live/delayed) require an explicit connect() before
    # any stream_* call. yfinance/replay/synthetic_options have no connect.
    feed_connected = False
    if hasattr(equity_feed, "connect"):
        try:
            await equity_feed.connect()
            feed_connected = True
            LOG.info("equity feed connected: %s", getattr(equity_feed, "name", "?"))
        except Exception as exc:
            # Use repr so audit captures the exception type even when the
            # message is empty (e.g. asyncio.TimeoutError has no str repr).
            LOG.error("equity feed connect failed: %r — engine will idle", exc)
            await _audit(writer, "engine", "FEED_CONNECT_FAILED", "ERROR",
                         repr(exc) or type(exc).__name__,
                         payload={"feed": cfg.data.feed})

    await _audit(writer, "engine", "STARTUP", "INFO",
                 f"engine started; feed={cfg.data.feed}", payload={
                     "feed": cfg.data.feed,
                     "broker_mode": cfg.broker.mode,
                     "dry_run": cfg.broker.dry_run,
                     "feed_connected": feed_connected,
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

    # Effective dry_run flag — starts at the YAML-configured value and is
    # overlaid each heartbeat with whatever the dashboard has set in the
    # runtime_settings.dry_run_override row (migration 0004). Letting the
    # operator flip broker.dry_run without redeploying is the whole point
    # of /live-enable.
    effective_dry_run = cfg.broker.dry_run

    async def _read_dry_run_override() -> bool | None:
        """Return the latest runtime_settings.dry_run_override.value, or None."""
        if not isinstance(storage, SupabaseBackend):
            return None
        try:
            rows = await storage.select(
                "runtime_settings", where={"key": "dry_run_override"}, limit=1,
            )
        except Exception as exc:
            LOG.warning("runtime_settings read failed: %s", exc)
            return None
        if not rows:
            return None
        v = rows[0].get("value")
        if isinstance(v, dict) and isinstance(v.get("value"), bool):
            return bool(v["value"])
        return None

    # Background heartbeat so the /status page shows the engine alive even
    # outside market hours when the bar stream is silent. Also writes a
    # BROKER_HEARTBEAT row containing the latest IBKR account snapshot
    # (account id, NAV, cash, buying power) so the dashboard can render
    # portfolio balance + connection state.
    async def _heartbeat() -> None:
        nonlocal effective_dry_run
        while not stop_event.is_set():
            override = await _read_dry_run_override()
            if override is not None and override != effective_dry_run:
                LOG.info(
                    "dry_run flipped via runtime_settings: %s -> %s",
                    effective_dry_run, override,
                )
                effective_dry_run = override
                # Tell the broker too — IBKRPaperBroker honors dry_run on every
                # place_order; toggling the attribute is enough for v1.
                if hasattr(broker, "dry_run"):
                    broker.dry_run = override   # type: ignore[attr-defined]
                await _audit(
                    writer, "engine", "DRY_RUN_FLIPPED", "WARN",
                    f"dry_run override applied: {override}",
                    payload={"new_value": override, "yaml_default": cfg.broker.dry_run},
                )

            await _audit(writer, "engine", "HEARTBEAT", "INFO",
                         "engine alive",
                         payload={"feed": cfg.data.feed,
                                  "dry_run": effective_dry_run})
            try:
                acct = await broker.get_account_summary()
                await _audit(
                    writer, "broker", "BROKER_HEARTBEAT", "INFO",
                    "ibkr account snapshot",
                    payload={
                        "account_id": acct.account_id,
                        "broker_mode": cfg.broker.mode,
                        "dry_run": effective_dry_run,
                        "nav": str(acct.net_liquidation),
                        "cash": str(acct.cash),
                        "buying_power": str(acct.buying_power),
                        "connected": True,
                    },
                )
            except Exception as exc:
                await _audit(
                    writer, "broker", "BROKER_ERROR", "WARN",
                    f"account_summary failed: {exc}",
                    payload={"connected": False, "error": str(exc)},
                )
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=60)
            except TimeoutError:
                pass

    heartbeat_task = asyncio.create_task(_heartbeat())

    async def _process_bar(bar) -> None:
        nonlocal open_positions
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
            premium = _intent_premium(intent, option_quotes)
            check: RiskCheck = risk.evaluate(
                intent=intent,
                account=account,
                open_positions=open_positions,
                realized_pnl_today=realized_pnl_today,
                last_premium=premium,
            )
            await writer.write_order_intent(intent, dry_run=effective_dry_run)
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

    async def _process_tick(quote) -> None:
        """Tick path: feed each NBBO to strategy.on_tick and process emissions."""
        nonlocal open_positions
        await writer.write_tick(quote, feed=cfg.data.feed)
        account = await broker.get_account_summary()

        # Pull current option chain ATM ±2 every N seconds (cheap once cached
        # by the IBKR feed). For now, refresh on every tick — the IBKRLiveFeed
        # handles caching internally; replay/yfinance feeds skip via early
        # return on empty chains.
        try:
            chain = await options_feed.get_option_chain(
                cfg.universe.symbol, quote.timestamp.date()
            )
        except Exception:
            chain = None

        option_quotes: list = []
        if chain and chain.contracts:
            quotes_iter = options_feed.stream_option_quotes(chain.contracts)
            try:
                # Drain just one snapshot per contract
                async for q in quotes_iter:
                    option_quotes.append(q)
                    if len(option_quotes) >= len(chain.contracts):
                        break
            except Exception:
                pass

        ctx = StrategyContext(
            now=quote.timestamp,
            last_tick=quote,
            option_quotes=option_quotes,
            open_positions=open_positions,
            cash_available=account.cash,
        )

        decision: StrategyDecision = strategy.on_tick(ctx)
        for sig in decision.signals:
            await writer.write_signal(sig)

        for intent in decision.intents:
            premium = _intent_premium(intent, option_quotes)
            check: RiskCheck = risk.evaluate(
                intent=intent,
                account=account,
                open_positions=open_positions,
                realized_pnl_today=realized_pnl_today,
                last_premium=premium,
            )
            await writer.write_order_intent(intent, dry_run=effective_dry_run)
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

    try:
        # Branch on strategy kind. Bar strategies consume bar streams; tick
        # strategies consume quote streams. Outer while-loop keeps the engine
        # alive when an inner stream exhausts (yfinance returns finite batches)
        # OR when the feed is disconnected (IBKR gateway booting).
        while not stop_event.is_set():
            # If the feed declared connect() and it failed, retry every 30s
            # rather than crash-looping the container.
            if hasattr(equity_feed, "connect") and not feed_connected:
                LOG.info("feed not connected; retrying in 30s")
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=30)
                except TimeoutError:
                    pass
                try:
                    await equity_feed.connect()
                    feed_connected = True
                    LOG.info("equity feed reconnected")
                except Exception as exc:
                    LOG.error("feed reconnect failed: %s", exc)
                    continue

            try:
                if getattr(strategy, "kind", "bar") == "tick":
                    async for quote in equity_feed.stream_equity_quotes(cfg.universe.symbol):
                        if stop_event.is_set():
                            break
                        await _process_tick(quote)
                else:
                    async for bar in equity_feed.stream_equity_bars(
                        cfg.universe.symbol, cfg.data.bar_interval_seconds
                    ):
                        if stop_event.is_set():
                            break
                        await _process_bar(bar)
            except RuntimeError as exc:
                if "not connected" in str(exc).lower():
                    LOG.warning("feed dropped connection mid-stream: %s", exc)
                    feed_connected = False
                    continue
                raise

            if stop_event.is_set():
                break
            try:
                await asyncio.wait_for(
                    stop_event.wait(), timeout=cfg.data.bar_interval_seconds
                )
            except TimeoutError:
                pass
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except (asyncio.CancelledError, Exception):
            pass
        await broker.disconnect()
        if feed_connected and hasattr(equity_feed, "disconnect"):
            try:
                await equity_feed.disconnect()
            except Exception:
                pass
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
