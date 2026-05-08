"""Writer round-trip + idempotency tests against the InMemoryBackend."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from contracts.broker import (
    Fill,
    OrderIntent,
    OrderSide,
    OrderType,
    Position,
    TimeInForce,
)
from contracts.data_feed import Bar, OptionContract, Quote
from contracts.strategy import Signal, SignalDirection
from services.persistence import (
    AuditEvent,
    InMemoryBackend,
    PersistenceWriter,
)


def _ts() -> datetime:
    return datetime(2026, 5, 7, 14, 30, tzinfo=UTC)


def _make_bar() -> Bar:
    return Bar(
        symbol="QQQ",
        interval_seconds=60,
        open_time=_ts(),
        open=Decimal("400.00"),
        high=Decimal("401.50"),
        low=Decimal("399.75"),
        close=Decimal("401.25"),
        volume=12345,
        vwap=Decimal("400.50"),
    )


def _make_intent() -> OrderIntent:
    return OrderIntent(
        intent_id=uuid4(),
        created_at=_ts(),
        symbol="QQQ",
        is_option=False,
        side=OrderSide.BUY,
        quantity=10,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        tag="unit-test",
    )


def _make_fill(intent: OrderIntent) -> Fill:
    return Fill(
        fill_id="F-1",
        intent_id=intent.intent_id,
        broker_order_id="B-1",
        timestamp=_ts(),
        symbol=intent.symbol,
        is_option=False,
        side=OrderSide.BUY,
        quantity=10,
        price=Decimal("401.25"),
        commission=Decimal("0.50"),
    )


def _make_position() -> Position:
    return Position(
        symbol="QQQ",
        is_option=False,
        quantity=10,
        avg_cost=Decimal("401.25"),
        market_value=Decimal("4012.50"),
        unrealized_pnl=Decimal("0"),
    )


def _make_option_position() -> Position:
    contract = OptionContract(
        underlying="QQQ",
        expiry=date(2026, 5, 16),
        strike=Decimal("405"),
        right="C",
    )
    return Position(
        symbol="QQQ",
        is_option=True,
        option=contract,
        quantity=2,
        avg_cost=Decimal("3.50"),
    )


@pytest.mark.asyncio
async def test_write_tick_round_trip() -> None:
    backend = InMemoryBackend()
    writer = PersistenceWriter(backend)
    quote = Quote(
        symbol="QQQ",
        timestamp=_ts(),
        bid=Decimal("400.00"),
        ask=Decimal("400.05"),
        last=Decimal("400.02"),
        volume=1000,
    )

    await writer.write_tick(quote, feed="yfinance")

    rows = await backend.select("ticks")
    assert len(rows) == 1
    assert rows[0]["symbol"] == "QQQ"
    assert rows[0]["bid"] == "400.00"
    assert rows[0]["feed"] == "yfinance"


@pytest.mark.asyncio
async def test_write_bar_is_idempotent_via_upsert() -> None:
    backend = InMemoryBackend()
    writer = PersistenceWriter(backend)
    bar = _make_bar()

    await writer.write_bar(bar, feed="yfinance")
    await writer.write_bar(bar, feed="yfinance")

    rows = await backend.select("bars")
    assert len(rows) == 1
    assert rows[0]["close"] == "401.25"


@pytest.mark.asyncio
async def test_write_signal_round_trip() -> None:
    backend = InMemoryBackend()
    writer = PersistenceWriter(backend)
    signal = Signal(
        name="sma9_vwap_cross",
        direction=SignalDirection.LONG_VOL_UP,
        timestamp=_ts(),
        symbol="QQQ",
        strength=Decimal("1.25"),
        metadata={"reason": "cross_up"},
    )

    await writer.write_signal(signal)

    rows = await backend.select("signals")
    assert len(rows) == 1
    assert rows[0]["direction"] == "LONG_VOL_UP"
    assert rows[0]["metadata"] == {"reason": "cross_up"}


@pytest.mark.asyncio
async def test_write_order_intent_idempotent() -> None:
    backend = InMemoryBackend()
    writer = PersistenceWriter(backend)
    intent = _make_intent()

    await writer.write_order_intent(intent, dry_run=True)
    await writer.write_order_intent(intent, dry_run=True)

    rows = await backend.select("order_intents")
    assert len(rows) == 1
    assert rows[0]["intent_id"] == str(intent.intent_id)
    assert rows[0]["dry_run"] is True


@pytest.mark.asyncio
async def test_write_fill_idempotent() -> None:
    backend = InMemoryBackend()
    writer = PersistenceWriter(backend)
    intent = _make_intent()
    fill = _make_fill(intent)

    await writer.write_order_intent(intent, dry_run=False)
    await writer.write_fill(fill)
    await writer.write_fill(fill)

    rows = await backend.select("fills")
    assert len(rows) == 1
    assert rows[0]["fill_id"] == "F-1"
    assert rows[0]["price"] == "401.25"


@pytest.mark.asyncio
async def test_write_position_idempotent_equity_and_option() -> None:
    backend = InMemoryBackend()
    writer = PersistenceWriter(backend)
    pos = _make_position()
    opt_pos = _make_option_position()

    await writer.write_position(pos)
    await writer.write_position(pos)
    await writer.write_position(opt_pos)
    await writer.write_position(opt_pos)

    rows = await backend.select("positions")
    assert len(rows) == 2
    quantities = sorted(r["quantity"] for r in rows)
    assert quantities == [2, 10]


@pytest.mark.asyncio
async def test_write_audit_round_trip() -> None:
    backend = InMemoryBackend()
    writer = PersistenceWriter(backend)
    event = AuditEvent(
        ts=_ts(),
        actor="risk",
        event_type="RISK_BLOCK",
        severity="WARN",
        message="quote stale",
        payload={"symbol": "QQQ"},
    )

    await writer.write_audit(event)

    rows = await backend.select("audit_log")
    assert len(rows) == 1
    assert rows[0]["event_type"] == "RISK_BLOCK"
    assert rows[0]["payload"] == {"symbol": "QQQ"}


@pytest.mark.asyncio
async def test_bump_daily_pnl_two_wins_and_one_loss() -> None:
    backend = InMemoryBackend()
    writer = PersistenceWriter(backend)
    today = date(2026, 5, 7)

    await writer.bump_daily_pnl(today, Decimal("100.00"), win=True)
    await writer.bump_daily_pnl(today, Decimal("50.00"), win=True)
    await writer.bump_daily_pnl(today, Decimal("-30.00"), win=False)

    rows = await backend.select("daily_pnl", where={"trading_day": today})
    assert len(rows) == 1
    row = rows[0]
    assert row["trades"] == 3
    assert row["wins"] == 2
    assert row["losses"] == 1
    assert Decimal(row["realized_usd"]) == Decimal("120.00")


@pytest.mark.asyncio
async def test_bump_daily_pnl_handles_none_win() -> None:
    backend = InMemoryBackend()
    writer = PersistenceWriter(backend)
    today = date(2026, 5, 7)

    await writer.bump_daily_pnl(today, Decimal("0"), win=None)
    await writer.bump_daily_pnl(today, Decimal("0"), win=True)

    rows = await backend.select("daily_pnl", where={"trading_day": today})
    assert rows[0]["trades"] == 2
    assert rows[0]["wins"] == 1
    assert rows[0]["losses"] == 0
