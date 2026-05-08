"""Tests for the walk-forward (in-sample / out-of-sample) split on Report."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from contracts.broker import OrderSide
from contracts.data_feed import OptionContract
from scripts.backtest import Report, TradeRecord


def _trade(entry_iso: str, pnl_pct: Decimal | None = Decimal("10")) -> TradeRecord:
    return TradeRecord(
        intent_id=uuid.uuid4(),
        entry_ts=datetime.fromisoformat(entry_iso),
        entry_price=Decimal("1.00"),
        side=OrderSide.BUY,
        contract=OptionContract(
            underlying="QQQ", expiry=date(2026, 4, 15),
            strike=Decimal("450"), right="C",
        ),
        pnl_pct=pnl_pct,
    )


def test_split_partitions_trades_by_entry_ts():
    report = Report(trades=[
        _trade("2026-04-15T13:30:00+00:00", pnl_pct=Decimal("5")),
        _trade("2026-04-15T14:00:00+00:00", pnl_pct=Decimal("10")),
        _trade("2026-04-15T14:30:00+00:00", pnl_pct=Decimal("-3")),  # OOS
        _trade("2026-04-15T15:00:00+00:00", pnl_pct=Decimal("8")),   # OOS
    ])
    split = datetime(2026, 4, 15, 14, 15, tzinfo=UTC)
    parts = report.split(split)

    assert parts["all"]["trades"] == 4
    assert parts["in_sample"]["trades"] == 2
    assert parts["out_of_sample"]["trades"] == 2
    # In-sample wins: 5% + 10% = both wins
    assert parts["in_sample"]["wins"] == 2
    # OOS: one win (8%), one loss (-3%)
    assert parts["out_of_sample"]["wins"] == 1
    assert parts["out_of_sample"]["losses"] == 1


def test_split_with_unclosed_trades_handled():
    """Trades with pnl_pct=None (still open) must not break the summarizer."""
    report = Report(trades=[
        _trade("2026-04-15T13:30:00+00:00", pnl_pct=Decimal("5")),
        _trade("2026-04-15T13:45:00+00:00", pnl_pct=None),
    ])
    parts = report.split(datetime(2026, 4, 15, 14, 0, tzinfo=UTC))
    # Open trades are excluded from win/loss counts
    assert parts["in_sample"]["trades"] == 1
    assert parts["all"]["trades"] == 1


def test_split_empty_report_safe():
    parts = Report(trades=[]).split(datetime(2026, 4, 15, 14, 0, tzinfo=UTC))
    assert parts["all"]["trades"] == 0
    assert parts["in_sample"]["trades"] == 0
    assert parts["out_of_sample"]["trades"] == 0
