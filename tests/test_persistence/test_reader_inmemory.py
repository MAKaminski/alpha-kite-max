"""Reader round-trip tests against the InMemoryBackend."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from contracts.broker import (
    Fill,
    OrderIntent,
    OrderSide,
    OrderType,
    Position,
)
from contracts.data_feed import Bar, Quote
from contracts.strategy import Signal, SignalDirection
from services.persistence import (
    AuditEvent,
    InMemoryBackend,
    PersistenceReader,
    PersistenceWriter,
)


def _ts(minute: int = 30) -> datetime:
    return datetime(2026, 5, 7, 14, minute, tzinfo=UTC)


@pytest.mark.asyncio
async def test_recent_signals_orders_newest_first() -> None:
    backend = InMemoryBackend()
    writer = PersistenceWriter(backend)
    reader = PersistenceReader(backend)

    older = Signal(
        name="s",
        direction=SignalDirection.LONG_VOL_UP,
        timestamp=_ts(10),
        symbol="QQQ",
    )
    newer = Signal(
        name="s",
        direction=SignalDirection.EXIT,
        timestamp=_ts(45),
        symbol="QQQ",
    )

    await writer.write_signal(older)
    await writer.write_signal(newer)

    rows = await reader.recent_signals(limit=10)
    assert len(rows) == 2
    assert rows[0]["direction"] == "EXIT"
    assert rows[1]["direction"] == "LONG_VOL_UP"


@pytest.mark.asyncio
async def test_open_positions_excludes_zero_quantity() -> None:
    backend = InMemoryBackend()
    writer = PersistenceWriter(backend)
    reader = PersistenceReader(backend)

    open_pos = Position(
        symbol="QQQ",
        is_option=False,
        quantity=10,
        avg_cost=Decimal("400"),
    )
    closed_pos = Position(
        symbol="SPY",
        is_option=False,
        quantity=0,
        avg_cost=Decimal("500"),
    )

    await writer.write_position(open_pos)
    await writer.write_position(closed_pos)

    rows = await reader.open_positions()
    assert len(rows) == 1
    assert rows[0]["symbol"] == "QQQ"


@pytest.mark.asyncio
async def test_daily_pnl_returns_recent_window() -> None:
    backend = InMemoryBackend()
    writer = PersistenceWriter(backend)
    reader = PersistenceReader(backend)

    today = date.today()
    yesterday = today - timedelta(days=1)

    await writer.bump_daily_pnl(today, Decimal("100"), win=True)
    await writer.bump_daily_pnl(yesterday, Decimal("-50"), win=False)

    rows = await reader.daily_pnl(days=30)
    assert len(rows) == 2
    # Most recent first because of order_by ts DESC on trading_day.
    assert rows[0].trading_day == today
    assert rows[0].realized_usd == Decimal("100")
    assert rows[0].wins == 1
    assert rows[1].trading_day == yesterday
    assert rows[1].losses == 1


@pytest.mark.asyncio
async def test_recent_audit_filters_by_severity() -> None:
    backend = InMemoryBackend()
    writer = PersistenceWriter(backend)
    reader = PersistenceReader(backend)

    await writer.write_audit(
        AuditEvent(_ts(10), "engine", "INFO_EVENT", "INFO", "noise", {})
    )
    await writer.write_audit(
        AuditEvent(_ts(20), "risk", "RISK_BLOCK", "WARN", "blocked", {})
    )
    await writer.write_audit(
        AuditEvent(_ts(30), "engine", "FATAL", "ERROR", "boom", {})
    )

    all_rows = await reader.recent_audit(limit=10)
    assert len(all_rows) == 3
    assert all_rows[0]["event_type"] == "FATAL"  # newest first

    warns_and_above = await reader.recent_audit(severity_min="WARN")
    severities = {r["severity"] for r in warns_and_above}
    assert severities == {"WARN", "ERROR"}

    errors_only = await reader.recent_audit(severity_min="ERROR")
    assert len(errors_only) == 1
    assert errors_only[0]["severity"] == "ERROR"


@pytest.mark.asyncio
async def test_full_round_trip_all_event_types() -> None:
    backend = InMemoryBackend()
    writer = PersistenceWriter(backend)
    reader = PersistenceReader(backend)

    quote = Quote(
        symbol="QQQ",
        timestamp=_ts(),
        bid=Decimal("400"),
        ask=Decimal("400.05"),
    )
    bar = Bar(
        symbol="QQQ",
        interval_seconds=60,
        open_time=_ts(),
        open=Decimal("400"),
        high=Decimal("401"),
        low=Decimal("399.5"),
        close=Decimal("400.75"),
        volume=1000,
    )
    signal = Signal(
        name="cross",
        direction=SignalDirection.LONG_VOL_UP,
        timestamp=_ts(),
        symbol="QQQ",
    )
    intent = OrderIntent(
        intent_id=uuid4(),
        created_at=_ts(),
        symbol="QQQ",
        is_option=False,
        side=OrderSide.BUY,
        quantity=5,
        order_type=OrderType.MARKET,
    )
    fill = Fill(
        fill_id="F-9",
        intent_id=intent.intent_id,
        broker_order_id="B-9",
        timestamp=_ts(),
        symbol="QQQ",
        is_option=False,
        side=OrderSide.BUY,
        quantity=5,
        price=Decimal("400.50"),
    )
    position = Position(
        symbol="QQQ",
        is_option=False,
        quantity=5,
        avg_cost=Decimal("400.50"),
    )
    audit = AuditEvent(_ts(), "engine", "ORDER_INTENT", "INFO", "submitted", {})

    await writer.write_tick(quote, feed="yfinance")
    await writer.write_bar(bar, feed="yfinance")
    await writer.write_signal(signal)
    await writer.write_order_intent(intent, dry_run=False)
    await writer.write_fill(fill)
    await writer.write_position(position)
    await writer.write_audit(audit)

    assert len(await backend.select("ticks")) == 1
    assert len(await backend.select("bars")) == 1
    assert len(await reader.recent_signals()) == 1
    assert len(await backend.select("order_intents")) == 1
    assert len(await backend.select("fills")) == 1
    assert len(await reader.open_positions()) == 1
    assert len(await reader.recent_audit()) == 1
