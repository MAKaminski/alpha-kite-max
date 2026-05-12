"""Extended unit tests for :class:`IBKRPaperBroker` — Layer 1 (no network).

These complement ``test_ibkr_paper_guard.py`` (paper-account guard) by
covering the rest of the broker contract:

  * Order-intent → ib_insync object translation (Stock/Option/Market/Limit/TIF)
  * Status-string → :class:`OrderStatus` enum mapping (all 8 IBKR values)
  * Synthetic event injection — drive ``orderStatusEvent`` and
    ``execDetailsEvent`` manually and assert the broker emits the right
    :class:`OrderUpdate` / :class:`Fill` shapes on its internal queues.
  * Audit-log payload shape for connect / place_order / disconnect.
  * Dry-run guarantees — :meth:`placeOrder` is never reached when
    ``dry_run=True``, even on a live-classified account.

NO network, NO Supabase, NO IBKR Gateway needed. Runs in CI by default.

Fallout-pattern: if these fail, the bug is in our wrapper code. Don't
bother with Layer 2 / 3 until this is green.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from contracts.broker import (
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)
from contracts.data_feed import OptionContract
from engine.broker import IBKRPaperBroker

# ─────────────────────────────────────────────────────────────────────────
# Fakes
# ─────────────────────────────────────────────────────────────────────────


class _Event:
    """Mimics ib_insync's Event surface (``+=`` to subscribe, ``emit`` to fire)."""

    def __init__(self) -> None:
        self._handlers: list[Any] = []

    def __iadd__(self, handler: Any) -> _Event:
        self._handlers.append(handler)
        return self

    def emit(self, *args: Any) -> None:
        for h in self._handlers:
            h(*args)


class _FakeRow:
    def __init__(self, account: str, tag: str, value: str) -> None:
        self.account = account
        self.tag = tag
        self.value = value


class _FakeOrder:
    def __init__(self) -> None:
        self.action: str | None = None
        self.totalQuantity: int | None = None
        self.lmtPrice: float | None = None
        self.tif: str | None = None
        self.orderId: int = 0


class _FakeOrderStatus:
    def __init__(self, status: str = "Submitted", filled: int = 0, avg: float = 0.0) -> None:
        self.status = status
        self.filled = filled
        self.avgFillPrice = avg


class _FakeTrade:
    def __init__(self, order: Any, contract: Any) -> None:
        self.order = order
        self.contract = contract
        self.orderStatus = _FakeOrderStatus()


class _FakeExecution:
    def __init__(
        self,
        exec_id: str,
        side: str,
        shares: int,
        price: float,
    ) -> None:
        self.execId = exec_id
        self.side = side  # "BOT" / "SLD"
        self.shares = shares
        self.price = price


class _FakeCommissionReport:
    def __init__(self, commission: float) -> None:
        self.commission = commission


class _FakeFillEvent:
    def __init__(self, execution: _FakeExecution, commission: float, contract: Any) -> None:
        self.execution = execution
        self.commissionReport = _FakeCommissionReport(commission)
        self.contract = contract


class _FakeIB:
    """Extended IB fake — captures ``placeOrder`` args + supports event emission."""

    def __init__(self, summary_rows: list[_FakeRow]) -> None:
        self._summary_rows = summary_rows
        self.connected = False
        self.last_place_contract: Any | None = None
        self.last_place_order: Any | None = None
        self.placed_orders: list[tuple[Any, Any]] = []
        self.cancelled_orders: list[Any] = []
        self._next_order_id = 100
        self.orderStatusEvent = _Event()
        self.execDetailsEvent = _Event()

    async def connectAsync(self, host: str, port: int, clientId: int) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def accountSummary(self) -> list[_FakeRow]:
        return list(self._summary_rows)

    def positions(self) -> list[Any]:
        return []

    def placeOrder(self, contract: Any, order: Any) -> Any:
        self.last_place_contract = contract
        self.last_place_order = order
        order.orderId = self._next_order_id
        self._next_order_id += 1
        self.placed_orders.append((contract, order))
        return _FakeTrade(order=order, contract=contract)

    def cancelOrder(self, order: Any) -> None:
        self.cancelled_orders.append(order)


def _paper_rows() -> list[_FakeRow]:
    return [
        _FakeRow("DU4286710", "AccountType", "DEMO"),
        _FakeRow("DU4286710", "NetLiquidation", "1000000"),
    ]


def _live_rows() -> list[_FakeRow]:
    return [
        _FakeRow("U1234567", "AccountType", "INDIVIDUAL"),
        _FakeRow("U1234567", "NetLiquidation", "100000"),
    ]


def _equity_intent(side: OrderSide = OrderSide.BUY, qty: int = 1) -> OrderIntent:
    return OrderIntent(
        intent_id=uuid4(),
        created_at=datetime.now(tz=UTC),
        symbol="QQQ",
        is_option=False,
        option=None,
        side=side,
        quantity=qty,
        order_type=OrderType.MARKET,
        limit_price=None,
        tag="unit-equity",
    )


def _limit_equity_intent(price: Decimal = Decimal("500.00")) -> OrderIntent:
    return OrderIntent(
        intent_id=uuid4(),
        created_at=datetime.now(tz=UTC),
        symbol="QQQ",
        is_option=False,
        option=None,
        side=OrderSide.BUY,
        quantity=1,
        order_type=OrderType.LIMIT,
        limit_price=price,
        time_in_force=TimeInForce.GTC,
        tag="unit-limit",
    )


def _option_intent() -> OrderIntent:
    contract = OptionContract(
        underlying="QQQ",
        expiry=date(2026, 5, 30),
        strike=Decimal("510"),
        right="C",
        multiplier=100,
    )
    return OrderIntent(
        intent_id=uuid4(),
        created_at=datetime.now(tz=UTC),
        symbol="QQQ",
        is_option=True,
        option=contract,
        side=OrderSide.BUY,
        quantity=1,
        order_type=OrderType.LIMIT,
        limit_price=Decimal("2.50"),
        tag="unit-option",
    )


async def _connected_broker(rows: list[_FakeRow], dry_run: bool = False) -> IBKRPaperBroker:
    fake = _FakeIB(rows)
    broker = IBKRPaperBroker(
        host="127.0.0.1", port=7497, client_id=1, dry_run=dry_run,
        paper_account_allowlist=["DEMO", "PAPER"], ib=fake,
    )
    await broker.connect()
    return broker


# ─────────────────────────────────────────────────────────────────────────
# Contract / order construction
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_equity_intent_builds_stock_contract() -> None:
    broker = await _connected_broker(_paper_rows())
    await broker.place_order(_equity_intent())
    contract = broker.ib.last_place_contract  # type: ignore[attr-defined]
    # ib_insync.Stock — verify symbol / exchange / currency
    assert contract.symbol == "QQQ"
    assert contract.exchange == "SMART"
    assert contract.currency == "USD"


@pytest.mark.asyncio
async def test_option_intent_builds_option_contract() -> None:
    broker = await _connected_broker(_paper_rows())
    await broker.place_order(_option_intent())
    contract = broker.ib.last_place_contract  # type: ignore[attr-defined]
    assert contract.symbol == "QQQ"
    assert contract.lastTradeDateOrContractMonth == "20260530"
    assert contract.strike == 510.0
    assert contract.right == "C"
    assert contract.exchange == "SMART"
    assert contract.multiplier == "100"


@pytest.mark.asyncio
async def test_market_order_routes_to_MarketOrder() -> None:
    broker = await _connected_broker(_paper_rows())
    await broker.place_order(_equity_intent(qty=3))
    order = broker.ib.last_place_order  # type: ignore[attr-defined]
    assert order.__class__.__name__ == "MarketOrder"
    assert order.action == "BUY"
    assert order.totalQuantity == 3


@pytest.mark.asyncio
async def test_limit_order_routes_to_LimitOrder_with_price() -> None:
    broker = await _connected_broker(_paper_rows())
    await broker.place_order(_limit_equity_intent(price=Decimal("499.50")))
    order = broker.ib.last_place_order  # type: ignore[attr-defined]
    assert order.__class__.__name__ == "LimitOrder"
    assert order.action == "BUY"
    assert order.totalQuantity == 1
    assert order.lmtPrice == 499.5


@pytest.mark.asyncio
async def test_sell_side_translates_to_SELL_action() -> None:
    broker = await _connected_broker(_paper_rows())
    await broker.place_order(_equity_intent(side=OrderSide.SELL))
    order = broker.ib.last_place_order  # type: ignore[attr-defined]
    assert order.action == "SELL"


@pytest.mark.parametrize(
    "tif,expected_ib",
    [
        (TimeInForce.DAY, "DAY"),
        (TimeInForce.GTC, "GTC"),
        (TimeInForce.IOC, "IOC"),
    ],
)
@pytest.mark.asyncio
async def test_tif_translation(tif: TimeInForce, expected_ib: str) -> None:
    broker = await _connected_broker(_paper_rows())
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
        time_in_force=tif,
        tag="tif",
    )
    await broker.place_order(intent)
    assert broker.ib.last_place_order.tif == expected_ib  # type: ignore[attr-defined]


# ─────────────────────────────────────────────────────────────────────────
# Status translation
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "ibkr_status,expected",
    [
        ("PendingSubmit", OrderStatus.PENDING_SUBMIT),
        ("PendingCancel", OrderStatus.PENDING_SUBMIT),
        ("PreSubmitted", OrderStatus.SUBMITTED),
        ("Submitted", OrderStatus.SUBMITTED),
        ("Filled", OrderStatus.FILLED),
        ("Cancelled", OrderStatus.CANCELLED),
        ("ApiCancelled", OrderStatus.CANCELLED),
        ("Inactive", OrderStatus.REJECTED),
        # Unknown values fall back to SUBMITTED so we never drop an update silently.
        ("SomeFutureStatus", OrderStatus.SUBMITTED),
        ("", OrderStatus.SUBMITTED),
    ],
)
def test_status_translation_table(ibkr_status: str, expected: OrderStatus) -> None:
    assert IBKRPaperBroker._translate_status(ibkr_status) == expected


# ─────────────────────────────────────────────────────────────────────────
# Synthetic event emission — the real value of this test layer.
# We simulate ib_insync firing orderStatusEvent / execDetailsEvent and
# assert the broker's internal queues receive correctly-shaped contract
# OrderUpdate / Fill objects.
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_order_status_event_produces_OrderUpdate_on_queue() -> None:
    broker = await _connected_broker(_paper_rows())
    intent = _equity_intent()
    await broker.place_order(intent)

    # The trade we just placed is the one ib_insync's event will reference.
    trade = broker._trades_by_intent[intent.intent_id]
    # Simulate IBKR pushing a "Filled" status update.
    trade.orderStatus.status = "Filled"
    trade.orderStatus.filled = 1
    trade.orderStatus.avgFillPrice = 500.25
    broker.ib.orderStatusEvent.emit(trade)  # type: ignore[attr-defined]

    updates = [u async for u in broker.stream_order_updates()]
    # First update from place_order is the synchronous response (SUBMITTED);
    # the event we just fired adds the FILLED one. Both flow through the same queue.
    statuses = [u.status for u in updates]
    assert OrderStatus.FILLED in statuses
    filled = next(u for u in updates if u.status == OrderStatus.FILLED)
    assert filled.intent_id == intent.intent_id
    assert filled.filled_qty == 1
    assert filled.avg_fill_price == Decimal("500.25")


@pytest.mark.asyncio
async def test_exec_details_event_produces_Fill_on_queue() -> None:
    broker = await _connected_broker(_paper_rows())
    intent = _equity_intent()
    await broker.place_order(intent)
    trade = broker._trades_by_intent[intent.intent_id]

    execution = _FakeExecution(exec_id="E-12345", side="BOT", shares=1, price=500.25)
    fill_event = _FakeFillEvent(
        execution=execution, commission=1.00, contract=trade.contract,
    )
    broker.ib.execDetailsEvent.emit(trade, fill_event)  # type: ignore[attr-defined]

    fills = [f async for f in broker.stream_fills()]
    assert len(fills) == 1
    f = fills[0]
    assert f.intent_id == intent.intent_id
    assert f.fill_id == "E-12345"
    assert f.symbol == "QQQ"
    assert f.is_option is False
    assert f.side == OrderSide.BUY
    assert f.quantity == 1
    assert f.price == Decimal("500.25")
    assert f.commission == Decimal("1.00")


@pytest.mark.asyncio
async def test_exec_details_event_for_option_includes_option_contract() -> None:
    broker = await _connected_broker(_paper_rows())
    intent = _option_intent()
    await broker.place_order(intent)
    trade = broker._trades_by_intent[intent.intent_id]
    # IBKR distinguishes option fills via contract.secType
    trade.contract.secType = "OPT"

    execution = _FakeExecution(exec_id="OPT-99", side="BOT", shares=1, price=2.50)
    fill_event = _FakeFillEvent(execution=execution, commission=0.65, contract=trade.contract)
    broker.ib.execDetailsEvent.emit(trade, fill_event)  # type: ignore[attr-defined]

    fills = [f async for f in broker.stream_fills()]
    assert len(fills) == 1
    f = fills[0]
    assert f.is_option is True
    assert f.option is not None
    assert f.option.right == "C"
    assert f.option.strike == Decimal("510")


@pytest.mark.asyncio
async def test_sell_side_in_exec_translates_correctly() -> None:
    """ib_insync uses 'BOT' for buy and 'SLD' for sell."""
    broker = await _connected_broker(_paper_rows())
    intent = _equity_intent(side=OrderSide.SELL)
    await broker.place_order(intent)
    trade = broker._trades_by_intent[intent.intent_id]

    execution = _FakeExecution(exec_id="E-SELL", side="SLD", shares=1, price=500.0)
    fill_event = _FakeFillEvent(execution=execution, commission=1.00, contract=trade.contract)
    broker.ib.execDetailsEvent.emit(trade, fill_event)  # type: ignore[attr-defined]

    fills = [f async for f in broker.stream_fills()]
    assert fills[0].side == OrderSide.SELL


# ─────────────────────────────────────────────────────────────────────────
# Audit-log shape
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_connect_emits_audit_with_expected_payload_shape() -> None:
    """The audit payload is what gets persisted to the audit_log table —
    its shape is part of our public contract with the persistence layer."""
    captured: list[tuple[str, dict[str, Any] | None]] = []
    fake = _FakeIB(_paper_rows())
    broker = IBKRPaperBroker(
        host="example", port=4002, client_id=42,
        dry_run=False, paper_account_allowlist=["DEMO"], ib=fake,
    )
    broker._audit = lambda msg, payload=None: captured.append((msg, payload))  # type: ignore[assignment]
    await broker.connect()

    connects = [c for c in captured if c[0] == "ibkr.connect"]
    assert len(connects) == 1
    payload = connects[0][1]
    assert payload is not None
    assert payload["host"] == "example"
    assert payload["port"] == 4002
    assert payload["client_id"] == 42
    assert payload["account_id"] == "DU4286710"
    assert payload["account_type"] in ("PAPER", "UNKNOWN")
    assert payload["dry_run"] is False


@pytest.mark.asyncio
async def test_place_order_emits_audit_with_intent_fields() -> None:
    captured: list[tuple[str, dict[str, Any] | None]] = []
    broker = await _connected_broker(_paper_rows())
    broker._audit = lambda msg, payload=None: captured.append((msg, payload))  # type: ignore[assignment]
    intent = _equity_intent(qty=2)
    await broker.place_order(intent)

    place_audits = [c for c in captured if c[0] == "ibkr.place_order"]
    assert len(place_audits) == 1
    payload = place_audits[0][1]
    assert payload is not None
    assert payload["intent_id"] == str(intent.intent_id)
    assert payload["symbol"] == "QQQ"
    assert payload["side"] == "BUY"
    assert payload["qty"] == 2
    assert payload["type"] == "MKT"
    assert payload["broker_order_id"]  # populated from fake's orderId


@pytest.mark.asyncio
async def test_disconnect_emits_audit() -> None:
    captured: list[tuple[str, dict[str, Any] | None]] = []
    broker = await _connected_broker(_paper_rows())
    broker._audit = lambda msg, payload=None: captured.append((msg, payload))  # type: ignore[assignment]
    await broker.disconnect()
    assert any(c[0] == "ibkr.disconnect" for c in captured)


# ─────────────────────────────────────────────────────────────────────────
# Dry-run guarantees — placeOrder must NEVER be called on the underlying IB
# when dry_run=True, even for a live-classified account.
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dry_run_on_live_account_does_not_reach_placeOrder() -> None:
    fake = _FakeIB(_live_rows())
    broker = IBKRPaperBroker(
        host="x", port=0, client_id=1, dry_run=True,
        paper_account_allowlist=["DEMO", "PAPER"], ib=fake,
    )
    await broker.connect()  # dry_run trumps paper-guard
    await broker.place_order(_equity_intent())
    assert fake.placed_orders == []  # NEVER hits the underlying broker


@pytest.mark.asyncio
async def test_dry_run_still_emits_dry_run_audit_event() -> None:
    captured: list[tuple[str, dict[str, Any] | None]] = []
    fake = _FakeIB(_paper_rows())
    broker = IBKRPaperBroker(
        host="x", port=0, client_id=1, dry_run=True,
        paper_account_allowlist=["DEMO"], ib=fake,
    )
    broker._audit = lambda msg, payload=None: captured.append((msg, payload))  # type: ignore[assignment]
    await broker.connect()
    await broker.place_order(_equity_intent())
    # We use the existing event name from the implementation.
    assert any(c[0] == "ibkr.place_order.dry_run" for c in captured)
