"""Round-trip tests for the in-memory DryRunBroker."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from contracts.broker import (
    AccountType,
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
)
from contracts.data_feed import OptionContract
from engine.broker import DryRunBroker, NotConnectedError


def _equity_intent(symbol: str = "QQQ", qty: int = 1, side: OrderSide = OrderSide.BUY) -> OrderIntent:
    return OrderIntent(
        intent_id=uuid4(),
        created_at=datetime.now(tz=UTC),
        symbol=symbol,
        is_option=False,
        option=None,
        side=side,
        quantity=qty,
        order_type=OrderType.MARKET,
        limit_price=None,
        tag="test",
    )


def _option_intent(qty: int = 1, side: OrderSide = OrderSide.BUY) -> OrderIntent:
    contract = OptionContract(
        underlying="QQQ",
        expiry=date(2026, 5, 15),
        strike=Decimal("500"),
        right="C",
    )
    return OrderIntent(
        intent_id=uuid4(),
        created_at=datetime.now(tz=UTC),
        symbol="QQQ",
        is_option=True,
        option=contract,
        side=side,
        quantity=qty,
        order_type=OrderType.LIMIT,
        limit_price=Decimal("2.50"),
        tag="opt-test",
    )


@pytest.mark.asyncio
async def test_round_trip_market_order_fills_and_updates_position() -> None:
    broker = DryRunBroker()
    await broker.connect()

    intent = _equity_intent(qty=1)
    update = await broker.place_order(intent)

    assert update.status == OrderStatus.FILLED
    assert update.intent_id == intent.intent_id
    assert update.filled_qty == 1
    assert update.avg_fill_price == Decimal("1.00")  # MKT fallback fill price

    positions = await broker.get_positions()
    assert len(positions) == 1
    pos = positions[0]
    assert pos.symbol == "QQQ"
    assert pos.is_option is False
    assert pos.quantity == 1
    assert pos.avg_cost == Decimal("1.00")

    # Drain the streams.
    fills = [f async for f in broker.stream_fills()]
    updates = [u async for u in broker.stream_order_updates()]
    assert len(fills) == 1
    assert fills[0].intent_id == intent.intent_id
    assert fills[0].quantity == 1
    assert len(updates) == 1
    assert updates[0].status == OrderStatus.FILLED


@pytest.mark.asyncio
async def test_account_summary_is_paper() -> None:
    broker = DryRunBroker()
    await broker.connect()
    summary = await broker.get_account_summary()
    assert summary.account_type == AccountType.PAPER
    assert summary.cash == Decimal("5000")
    assert summary.buying_power == Decimal("5000")
    assert summary.net_liquidation == Decimal("5000")


@pytest.mark.asyncio
async def test_dry_run_is_dry_run_flag_true() -> None:
    broker = DryRunBroker()
    assert broker.dry_run is True
    assert broker.name == "dry_run"


@pytest.mark.asyncio
async def test_methods_require_connect() -> None:
    broker = DryRunBroker()
    intent = _equity_intent()
    with pytest.raises(NotConnectedError):
        await broker.place_order(intent)
    with pytest.raises(NotConnectedError):
        await broker.get_account_summary()
    with pytest.raises(NotConnectedError):
        await broker.get_positions()


@pytest.mark.asyncio
async def test_limit_order_uses_limit_price() -> None:
    broker = DryRunBroker()
    await broker.connect()
    intent = _option_intent(qty=2)
    update = await broker.place_order(intent)
    assert update.status == OrderStatus.FILLED
    assert update.avg_fill_price == Decimal("2.50")
    positions = await broker.get_positions()
    assert len(positions) == 1
    assert positions[0].is_option is True
    assert positions[0].quantity == 2
    assert positions[0].avg_cost == Decimal("2.50")


@pytest.mark.asyncio
async def test_buy_then_sell_flattens_position() -> None:
    broker = DryRunBroker()
    await broker.connect()
    buy = _equity_intent(qty=2, side=OrderSide.BUY)
    await broker.place_order(buy)
    sell = _equity_intent(qty=2, side=OrderSide.SELL)
    await broker.place_order(sell)
    positions = await broker.get_positions()
    assert positions == []  # flat positions filtered out


@pytest.mark.asyncio
async def test_disconnect_clears_connected_flag() -> None:
    broker = DryRunBroker()
    await broker.connect()
    await broker.disconnect()
    with pytest.raises(NotConnectedError):
        await broker.get_account_summary()


@pytest.mark.asyncio
async def test_cancel_returns_cancelled_update() -> None:
    broker = DryRunBroker()
    await broker.connect()
    intent_id = uuid4()
    update = await broker.cancel_order(intent_id)
    assert update.status == OrderStatus.CANCELLED
    assert update.intent_id == intent_id
