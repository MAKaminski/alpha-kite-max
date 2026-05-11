"""End-to-end backtest driver.

Reads bars from a fixture (replay feed), runs the configured strategy
against synthetic options, simulates paper fills via DryRunBroker, then
prints an expectancy report.

Usage:
    python scripts/backtest.py --config config/strategy.yaml \
        --fixture tests/fixtures/qqq_2026-04-15_1min.json
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from config.schema import load_config
from contracts.broker import OrderSide
from contracts.data_feed import Bar, OptionContract, OptionQuote
from contracts.strategy import StrategyContext, StrategyDecision
from engine.broker.dry_run import DryRunBroker
from engine.data_feeds.replay import ReplayFeed
from engine.data_feeds.synthetic_options import SyntheticOptionsFeed
from engine.risk.kill_switch import KillSwitchGuard
from engine.risk.limits import (
    DailyLossLimitGuard,
    MaxOpenPositionsGuard,
    MaxPremiumPctNavGuard,
)
from engine.risk.paper_guard import PaperAccountGuard
from engine.risk.pipeline import RiskPipeline
from engine.strategies.buy_vol_qqq_cross import BuyVolQQQCrossStrategy

LOG = logging.getLogger("alpha_kite.backtest")


@dataclass
class TradeRecord:
    intent_id: uuid.UUID
    entry_ts: datetime
    entry_price: Decimal
    side: OrderSide
    contract: OptionContract
    exit_ts: datetime | None = None
    exit_price: Decimal | None = None
    pnl_pct: Decimal | None = None
    reason: str = ""


@dataclass
class Report:
    trades: list[TradeRecord] = field(default_factory=list)

    def summary(self) -> dict:
        return _summarize(self.trades)

    def split(self, split_date: datetime) -> dict:
        """Partition trades by ``entry_ts`` against ``split_date``.

        Returns a dict with ``in_sample`` / ``out_of_sample`` summaries plus
        the original ``all`` summary, so callers can render side-by-side
        statistics without re-running the strategy.
        """
        in_sample = [t for t in self.trades if t.entry_ts < split_date]
        oos = [t for t in self.trades if t.entry_ts >= split_date]
        return {
            "split_date": split_date.isoformat(),
            "all": _summarize(self.trades),
            "in_sample": _summarize(in_sample),
            "out_of_sample": _summarize(oos),
        }


def _summarize(trades: list[TradeRecord]) -> dict:
    closed = [t for t in trades if t.pnl_pct is not None]
    wins = [t for t in closed if t.pnl_pct > 0]
    losses = [t for t in closed if t.pnl_pct <= 0]
    n = len(closed)
    win_rate = (len(wins) / n) if n else 0.0
    avg_win = float(sum(t.pnl_pct for t in wins) / len(wins)) if wins else 0.0
    avg_loss = (
        float(sum(t.pnl_pct for t in losses) / len(losses)) if losses else 0.0
    )
    expectancy = float(sum(t.pnl_pct for t in closed) / n) if n else 0.0
    total = float(sum(t.pnl_pct for t in closed)) if closed else 0.0
    return {
        "trades": n,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(win_rate * 100, 2),
        "avg_win_pct": round(avg_win, 2),
        "avg_loss_pct": round(avg_loss, 2),
        "expectancy_pct": round(expectancy, 2),
        "total_pnl_pct": round(total, 2),
    }


async def _quote_for(
    quotes: list[OptionQuote], contract: OptionContract
) -> OptionQuote | None:
    for q in quotes:
        if (
            q.strike == contract.strike
            and q.right == contract.right
            and q.expiry == contract.expiry
        ):
            return q
    return None


async def run_backtest(
    config_path: str,
    fixture_path: str | None = None,
    *,
    symbol: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    interval_seconds: int = 60,
    dsn: str | None = None,
) -> Report:
    """Run the configured strategy through historical bars and return a Report.

    Bars source: pass ``fixture_path`` (replay JSON) OR pass ``symbol`` +
    ``start`` + ``end`` (Supabase ``bars`` table). The DB path uses the env
    var ``SUPABASE_DB_URL`` by default; override via ``dsn``.
    """
    cfg = load_config(config_path)

    feed: ReplayFeed | SupabaseBarsFeed
    if fixture_path is not None:
        LOG.info("backtest start: source=fixture fixture=%s mode=%s",
                 fixture_path, cfg.entry.mode)
        feed = ReplayFeed(fixture_path)
    else:
        if not (symbol and start and end):
            raise ValueError(
                "run_backtest requires either fixture_path, or symbol+start+end",
            )
        from engine.data_feeds.supabase_bars import SupabaseBarsFeed
        actual_dsn = dsn or os.getenv("SUPABASE_DB_URL")
        if not actual_dsn:
            raise ValueError(
                "SUPABASE_DB_URL is not set; cannot pull bars from the database",
            )
        LOG.info("backtest start: source=supabase symbol=%s %s..%s @%ds mode=%s",
                 symbol, start.isoformat(), end.isoformat(), interval_seconds,
                 cfg.entry.mode)
        feed = SupabaseBarsFeed(
            actual_dsn, symbol=symbol, start=start, end=end,
            interval_seconds=interval_seconds,
        )
    options_feed = SyntheticOptionsFeed(feed)
    strategy = BuyVolQQQCrossStrategy(
        symbol=cfg.universe.symbol,
        sma_period=cfg.signal.params.sma_period,
        mode=cfg.entry.mode,
        contracts=cfg.entry.contracts,
        profit_target_pct=cfg.exit.profit_target_pct,
        stop_loss_pct=cfg.exit.stop_loss_pct,
        time_stop_minutes_before_close=cfg.exit.time_stop_minutes_before_close,
    )
    risk = RiskPipeline(
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
    broker = DryRunBroker()
    await broker.connect()

    bar_history: list[Bar] = []
    open_records: dict[uuid.UUID, TradeRecord] = {}
    report = Report()
    # Track the date of the previous bar so we can reset the strategy's
    # intraday state at session boundaries. Without this, multi-day
    # backtests carry prior-day bars into VWAP/SMA buffers and crosses
    # almost never fire after the first day. (See engine.strategies.
    # buy_vol_qqq_cross.BuyVolQQQCrossStrategy.reset_session for why.)
    prev_session_date: date | None = None

    # When pulling from Supabase, use the caller-supplied interval; for
    # fixtures the value is fixed by the JSON schema.
    stream_interval = (
        interval_seconds if fixture_path is None else cfg.data.bar_interval_seconds
    )
    async for bar in feed.stream_equity_bars(
        cfg.universe.symbol, stream_interval
    ):
        if prev_session_date is not None and bar.open_time.date() != prev_session_date:
            strategy.reset_session()
        prev_session_date = bar.open_time.date()

        bar_history.append(bar)

        chain = await options_feed.get_option_chain(
            cfg.universe.symbol, bar.open_time.date()
        )
        oqs: list[OptionQuote] = []
        async for q in options_feed.stream_option_quotes(chain.contracts):
            oqs.append(q)
            if len(oqs) >= len(chain.contracts):
                break

        # Drive exits on option quote tick
        if open_records:
            ctx_exit = StrategyContext(
                now=bar.open_time,
                last_bar=bar,
                bar_history=bar_history[-200:],
                option_quotes=oqs,
                open_positions=len(open_records),
                cash_available=Decimal("5000"),
            )
            decision_exit = strategy.on_option_quote(ctx_exit)
            await _process_decision(
                decision_exit, oqs, broker, risk, open_records, report, exit_pass=True
            )

        ctx = StrategyContext(
            now=bar.open_time,
            last_bar=bar,
            bar_history=bar_history[-200:],
            option_quotes=oqs,
            open_positions=len(open_records),
            cash_available=Decimal("5000"),
        )
        decision = strategy.on_bar(ctx)
        await _process_decision(
            decision, oqs, broker, risk, open_records, report, exit_pass=False
        )

    # Sweep any positions still open when the fixture's bars ran out. We
    # can't compute a realistic exit P&L without future data, so leave
    # pnl_pct=None — the summary excludes these from win/loss/expectancy
    # stats, but the trade ledger in the UI lists them so the user sees
    # entries fired even if the fixture was too short for an exit.
    for _intent_id, rec in list(open_records.items()):
        rec.reason = "open_at_fixture_end"
        report.trades.append(rec)
    open_records.clear()

    await broker.disconnect()
    if hasattr(feed, "close"):
        await feed.close()
    return report


async def _process_decision(
    decision: StrategyDecision,
    option_quotes: list[OptionQuote],
    broker: DryRunBroker,
    risk: RiskPipeline,
    open_records: dict[uuid.UUID, TradeRecord],
    report: Report,
    exit_pass: bool,
) -> None:
    account = await broker.get_account_summary()
    for intent in decision.intents:
        premium = intent.limit_price or Decimal("1")
        check = risk.evaluate(
            intent=intent,
            account=account,
            open_positions=len(open_records),
            realized_pnl_today=Decimal("0"),
            last_premium=premium,
        )
        if not check.allowed:
            LOG.info("intent blocked: %s", check.reasons)
            continue

        update = await broker.place_order(intent)
        fill_price = update.avg_fill_price or premium

        if intent.side == OrderSide.BUY:
            rec = TradeRecord(
                intent_id=intent.intent_id,
                entry_ts=intent.created_at,
                entry_price=fill_price,
                side=intent.side,
                contract=intent.option,  # type: ignore[arg-type]
            )
            open_records[intent.intent_id] = rec
        else:  # SELL — close a matching open record
            match_id = _find_open_for_contract(open_records, intent.option)
            if match_id is None:
                continue
            rec = open_records.pop(match_id)
            rec.exit_ts = intent.created_at
            rec.exit_price = fill_price
            if rec.entry_price > 0:
                rec.pnl_pct = (
                    (rec.exit_price - rec.entry_price) / rec.entry_price * Decimal("100")
                )
            rec.reason = intent.tag
            report.trades.append(rec)


def _find_open_for_contract(
    open_records: dict[uuid.UUID, TradeRecord], contract: OptionContract | None
) -> uuid.UUID | None:
    if contract is None:
        return None
    for k, v in open_records.items():
        if (
            v.contract.strike == contract.strike
            and v.contract.right == contract.right
            and v.contract.expiry == contract.expiry
        ):
            return k
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="alpha-kite-v2 backtest")
    parser.add_argument("--config", default="config/strategy.yaml")
    parser.add_argument(
        "--fixture", default="tests/fixtures/qqq_2026-04-15_1min.json"
    )
    parser.add_argument(
        "--split-date",
        default=None,
        help=(
            "Optional ISO timestamp (e.g. 2026-04-15T15:00Z). When set, the "
            "backtest partitions trades into in-sample (entry_ts < split) "
            "and out-of-sample (entry_ts >= split) and prints both reports."
        ),
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if not Path(args.fixture).exists():
        raise SystemExit(f"fixture not found: {args.fixture}")

    report = asyncio.run(run_backtest(args.config, args.fixture))

    if args.split_date is None:
        _print_summary("backtest report", args.fixture, report.summary())
        return

    split = datetime.fromisoformat(args.split_date.replace("Z", "+00:00"))
    parts = report.split(split)
    print(f"\nfixture:    {args.fixture}")
    print(f"split:      {parts['split_date']}\n")
    _print_summary("ALL trades", args.fixture, parts["all"])
    _print_summary("IN-SAMPLE  (entry_ts < split)", args.fixture, parts["in_sample"])
    _print_summary("OUT-OF-SAMPLE (entry_ts >= split)", args.fixture, parts["out_of_sample"])


def _print_summary(title: str, fixture: str, summary: dict) -> None:
    print(f"──────── {title} ────────")
    print(f"trades:     {summary['trades']}")
    print(f"wins:       {summary['wins']}")
    print(f"losses:     {summary['losses']}")
    print(f"win rate:   {summary['win_rate_pct']}%")
    print(f"avg win:    {summary['avg_win_pct']}%")
    print(f"avg loss:   {summary['avg_loss_pct']}%")
    print(f"expectancy: {summary['expectancy_pct']}% per trade")
    print(f"total P&L:  {summary['total_pnl_pct']}%")
    print("───────────────────────────────────────────────\n")
    if summary["trades"] == 0:
        print("(0 trades — fixture may not have produced a cross + exit pair)\n")


if __name__ == "__main__":
    main()
