"""Fail-closed paper-guard tests for `IBKRPaperBroker`.

The real `ib_insync.IB` is replaced with a tiny fake. We assert:

  * dry_run=False with a LIVE account ⇒ NonPaperAccountError
  * dry_run=False with a DU* paper account ⇒ connect succeeds
  * dry_run=True with any account ⇒ connect succeeds (dry_run trumps the guard)
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from contracts.broker import OrderIntent, OrderSide, OrderStatus, OrderType
from engine.broker import IBKRPaperBroker, NonPaperAccountError, NotConnectedError


class _FakeRow:
    """Mimics ib_insync.AccountValue (NamedTuple-like)."""

    def __init__(self, account: str, tag: str, value: str, currency: str = "USD", modelCode: str = "") -> None:
        self.account = account
        self.tag = tag
        self.value = value
        self.currency = currency
        self.modelCode = modelCode


class _FakeIB:
    """Stand-in for `ib_insync.IB` that records calls without touching a socket."""

    def __init__(self, summary_rows: list[_FakeRow]) -> None:
        self._summary_rows = summary_rows
        self.connected = False
        self.placed_orders: list[Any] = []
        self.cancelled_orders: list[Any] = []
        # Real IB exposes Event objects; we don't bother — ibkr_paper handles
        # missing/strange event attrs gracefully.
        self.orderStatusEvent = None
        self.execDetailsEvent = None

    async def connectAsync(self, host: str, port: int, clientId: int) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def accountSummary(self) -> list[_FakeRow]:
        return list(self._summary_rows)

    def positions(self) -> list[Any]:
        return []

    def placeOrder(self, contract: Any, order: Any) -> Any:
        self.placed_orders.append((contract, order))
        # Minimal Trade-like object.
        order.orderId = 42
        return _FakeTrade(order=order, contract=contract)

    def cancelOrder(self, order: Any) -> None:
        self.cancelled_orders.append(order)


class _FakeOrderStatus:
    def __init__(self, status: str = "Filled", filled: int = 1, avg: float = 1.23) -> None:
        self.status = status
        self.filled = filled
        self.avgFillPrice = avg


class _FakeTrade:
    def __init__(self, order: Any, contract: Any) -> None:
        self.order = order
        self.contract = contract
        self.orderStatus = _FakeOrderStatus()


def _live_summary() -> list[_FakeRow]:
    return [
        _FakeRow(account="U1234567", tag="AccountType", value="INDIVIDUAL"),
        _FakeRow(account="U1234567", tag="NetLiquidation", value="100000"),
    ]


def _paper_summary() -> list[_FakeRow]:
    return [
        _FakeRow(account="DU1234567", tag="AccountType", value="DEMO"),
        _FakeRow(account="DU1234567", tag="NetLiquidation", value="1000000"),
    ]


@pytest.mark.asyncio
async def test_live_account_with_dry_run_false_is_refused() -> None:
    fake_ib = _FakeIB(_live_summary())
    broker = IBKRPaperBroker(
        host="127.0.0.1",
        port=7497,
        client_id=1,
        dry_run=False,
        paper_account_allowlist=["DEMO", "PAPER"],
        ib=fake_ib,
    )
    with pytest.raises(NonPaperAccountError):
        await broker.connect()
    assert broker._connected is False  # fail-closed


@pytest.mark.asyncio
async def test_paper_account_du_prefix_passes_guard() -> None:
    fake_ib = _FakeIB(_paper_summary())
    broker = IBKRPaperBroker(
        host="127.0.0.1",
        port=7497,
        client_id=1,
        dry_run=False,
        paper_account_allowlist=["DEMO", "PAPER"],
        ib=fake_ib,
    )
    await broker.connect()
    assert broker._connected is True


@pytest.mark.asyncio
async def test_dry_run_trumps_guard_on_live_account() -> None:
    fake_ib = _FakeIB(_live_summary())
    broker = IBKRPaperBroker(
        host="127.0.0.1",
        port=7497,
        client_id=1,
        dry_run=True,
        paper_account_allowlist=["DEMO", "PAPER"],
        ib=fake_ib,
    )
    await broker.connect()
    assert broker._connected is True

    # And `place_order` must NOT call `placeOrder` on the underlying IB.
    intent = OrderIntent(
        intent_id=uuid4(),
        created_at=datetime.now(tz=UTC),
        symbol="QQQ",
        is_option=False,
        option=None,
        side=OrderSide.BUY,
        quantity=1,
        order_type=OrderType.MARKET,
        limit_price=None,
        tag="dry-on-live",
    )
    update = await broker.place_order(intent)
    assert update.status == OrderStatus.FILLED
    assert fake_ib.placed_orders == []  # short-circuited by dry_run


@pytest.mark.asyncio
async def test_paper_substring_match_in_allowlist() -> None:
    """Allowlist substring should match against the AccountType tag."""
    rows = [
        _FakeRow(account="X9999999", tag="AccountType", value="paper-trading"),
        _FakeRow(account="X9999999", tag="NetLiquidation", value="50000"),
    ]
    fake_ib = _FakeIB(rows)
    broker = IBKRPaperBroker(
        host="127.0.0.1",
        port=7497,
        client_id=1,
        dry_run=False,
        paper_account_allowlist=["paper", "demo"],
        ib=fake_ib,
    )
    await broker.connect()
    assert broker._connected is True


@pytest.mark.asyncio
async def test_methods_require_connect_on_ibkr_broker() -> None:
    fake_ib = _FakeIB(_paper_summary())
    broker = IBKRPaperBroker(dry_run=True, ib=fake_ib)
    intent = OrderIntent(
        intent_id=uuid4(),
        created_at=datetime.now(tz=UTC),
        symbol="QQQ",
        is_option=False,
        option=None,
        side=OrderSide.BUY,
        quantity=1,
        order_type=OrderType.MARKET,
        limit_price=None,
        tag="not-connected",
    )
    with pytest.raises(NotConnectedError):
        await broker.place_order(intent)


@pytest.mark.asyncio
async def test_disconnect_clears_state() -> None:
    fake_ib = _FakeIB(_paper_summary())
    broker = IBKRPaperBroker(dry_run=True, ib=fake_ib)
    await broker.connect()
    await broker.disconnect()
    assert broker._connected is False
    assert fake_ib.connected is False


@pytest.mark.asyncio
async def test_account_summary_in_dry_run_uses_real_account_id() -> None:
    fake_ib = _FakeIB(_paper_summary())
    broker = IBKRPaperBroker(dry_run=True, ib=fake_ib)
    await broker.connect()
    summary = await broker.get_account_summary()
    assert summary.account_id == "DU1234567"
    # PAPER because the underlying account is a DU* paper account.
    # AccountType is set to PAPER by classifier when value is "DEMO".
    assert summary.account_type.value == "PAPER"
    # Cash/NAV come from the dry-run inner broker.
    assert summary.cash == Decimal("5000")
