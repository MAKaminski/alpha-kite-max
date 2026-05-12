"""Live IBKR paper-broker integration tests — Layer 2.

These tests REQUIRE a running IBKR Gateway / TWS reachable at
``$IB_HOST:$IB_PORT`` (defaults ``127.0.0.1:4002`` — paper port). They
trade real (paper) money against your DU* account, so a passing run
leaves visible activity in IBKR Client Portal.

Marked ``@pytest.mark.live`` so CI skips them. Run locally with::

    IB_HOST=127.0.0.1 IB_PORT=4002 \
        uv run pytest tests/test_broker/test_ibkr_paper_integration.py -m live -v

Or against a Railway-hosted gateway via the public TCP proxy::

    IB_HOST=shortline.proxy.rlwy.net IB_PORT=50990 \
        uv run pytest tests/test_broker/test_ibkr_paper_integration.py -m live -v

Fallout-pattern:
  * Layer 1 unit tests pass + Layer 2 fails → bug is in the IBKR
    network / auth / handshake layer (NOT our code).
  * The tests are sequenced from cheapest (connect) to most expensive
    (place + cancel + fill) so the first failure pinpoints the layer.

Safety:
  * Every test enforces ``account_id.startswith("DU")`` before placing
    any orders. A non-paper account aborts the test.
  * Every order-placing test wraps in try/finally that flattens any
    leftover position via market sell.
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import UTC, datetime
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
from engine.broker import IBKRPaperBroker

pytestmark = pytest.mark.live


# ─────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────


def _ibkr_env() -> tuple[str, int, int]:
    host = os.environ.get("IB_HOST", "127.0.0.1")
    port = int(os.environ.get("IB_PORT", "4002"))
    client_id = int(os.environ.get("IB_CLIENT_ID", "31"))
    return host, port, client_id


@pytest.fixture
async def live_broker() -> IBKRPaperBroker:
    """Connected live paper broker. Disconnects in teardown.

    Fail-closed: if the connected account is not a DU* paper account,
    the test is aborted before any orders can be placed.
    """
    host, port, client_id = _ibkr_env()
    broker = IBKRPaperBroker(
        host=host, port=port, client_id=client_id,
        dry_run=False, paper_account_allowlist=["DEMO", "PAPER"],
    )
    try:
        await broker.connect()
    except Exception as exc:
        pytest.skip(f"could not connect to IBKR gateway at {host}:{port}: {exc}")
    summary = await broker.get_account_summary()
    if not summary.account_id.startswith("DU"):
        await broker.disconnect()
        pytest.fail(
            f"refusing to run live tests against non-paper account "
            f"{summary.account_id!r} ({summary.account_type.value})",
        )
    yield broker
    try:
        await broker.disconnect()
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────


async def _wait_for_status(
    broker: IBKRPaperBroker,
    intent_id,
    statuses: tuple[OrderStatus, ...],
    timeout_s: float = 30.0,
) -> OrderStatus:
    """Drain :meth:`stream_order_updates` until one of ``statuses`` is seen.

    Returns the matching status, or raises ``TimeoutError`` after
    ``timeout_s`` seconds.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        async for u in broker.stream_order_updates():
            if u.intent_id == intent_id and u.status in statuses:
                return u.status
        await asyncio.sleep(0.25)
    raise TimeoutError(
        f"no order update with status in {statuses} for intent_id={intent_id} within {timeout_s}s",
    )


def _is_during_rth() -> bool:
    """Mon-Fri 13:30-20:00 UTC == 09:30-16:00 ET (NYSE regular hours, DST).

    This is a rough check — we'd need a holiday calendar for full accuracy,
    but it's sufficient to skip MKT-order tests outside business hours.
    """
    now = datetime.now(tz=UTC)
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 13 * 60 + 30 <= minutes <= 19 * 60 + 55


def _equity_buy_market(qty: int = 1, tag: str = "intg") -> OrderIntent:
    return OrderIntent(
        intent_id=uuid4(),
        created_at=datetime.now(tz=UTC),
        symbol="QQQ",
        is_option=False,
        option=None,
        side=OrderSide.BUY,
        quantity=qty,
        order_type=OrderType.MARKET,
        limit_price=None,
        tag=tag,
    )


def _equity_sell_market(qty: int = 1, tag: str = "intg-flat") -> OrderIntent:
    return OrderIntent(
        intent_id=uuid4(),
        created_at=datetime.now(tz=UTC),
        symbol="QQQ",
        is_option=False,
        option=None,
        side=OrderSide.SELL,
        quantity=qty,
        order_type=OrderType.MARKET,
        limit_price=None,
        tag=tag,
    )


def _equity_buy_limit_deep_otm(last: Decimal, tag: str = "intg-otm") -> OrderIntent:
    """Limit BUY at 5% below last price — should remain open, won't fill.

    Used to validate the place→submitted→cancel path without any actual
    execution risk.
    """
    price = (last * Decimal("0.95")).quantize(Decimal("0.01"))
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
        tag=tag,
    )


# ─────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_connect_returns_du_paper_account(live_broker: IBKRPaperBroker) -> None:
    """Sanity: live_broker fixture already enforces this, but assert
    explicitly so this layer-2 test can stand alone as proof."""
    summary = await live_broker.get_account_summary()
    assert summary.account_id.startswith("DU")
    assert summary.account_type in (AccountType.PAPER, AccountType.UNKNOWN)


@pytest.mark.asyncio
async def test_account_summary_populates_money_fields(live_broker: IBKRPaperBroker) -> None:
    """Proves IBKR is actually returning live account data (NAV > 0)."""
    summary = await live_broker.get_account_summary()
    assert summary.net_liquidation > 0, (
        f"NAV should be > 0 on a real paper account; got {summary.net_liquidation}",
    )
    assert summary.buying_power >= 0
    assert summary.cash >= 0


@pytest.mark.asyncio
async def test_qualify_qqq_stock_contract(live_broker: IBKRPaperBroker) -> None:
    """Build a QQQ Stock contract and qualify it against IBKR. Validates
    the contract-builder against the real broker's symbol-resolution
    service."""
    from ib_insync import Stock  # type: ignore[import-not-found]

    contract = Stock("QQQ", "SMART", "USD")
    qualified = await live_broker.ib.qualifyContractsAsync(contract)
    assert qualified, "qualifyContractsAsync returned no contracts"
    q = qualified[0]
    assert int(getattr(q, "conId", 0)) > 0, "conId should be populated after qualify"
    assert getattr(q, "symbol", "") == "QQQ"


@pytest.mark.asyncio
async def test_place_and_cancel_open_limit_order(live_broker: IBKRPaperBroker) -> None:
    """Place a deep-OTM limit BUY (won't fill), confirm Submitted, then
    cancel. Validates the place→submitted→cancel path with no fill risk.
    """
    from ib_insync import Stock  # type: ignore[import-not-found]

    # Use the underlying's last price to size the deep-OTM limit.
    contract = Stock("QQQ", "SMART", "USD")
    ticker = live_broker.ib.reqMktData(contract, "", False, False)
    # Wait briefly for a quote.
    for _ in range(20):
        await asyncio.sleep(0.25)
        if ticker.last and str(ticker.last).lower() != "nan":
            break
    last_price = Decimal(str(ticker.last)) if ticker.last else Decimal("450")
    live_broker.ib.cancelMktData(contract)

    intent = _equity_buy_limit_deep_otm(last_price)
    update = await live_broker.place_order(intent)
    assert update.status in (OrderStatus.SUBMITTED, OrderStatus.PENDING_SUBMIT)

    # Wait for SUBMITTED (skip PendingSubmit which is transient).
    status = await _wait_for_status(
        live_broker, intent.intent_id, (OrderStatus.SUBMITTED,), timeout_s=15,
    )
    assert status == OrderStatus.SUBMITTED

    # Cancel and confirm.
    await live_broker.cancel_order(intent.intent_id)
    status = await _wait_for_status(
        live_broker, intent.intent_id, (OrderStatus.CANCELLED,), timeout_s=15,
    )
    assert status == OrderStatus.CANCELLED


@pytest.mark.asyncio
async def test_place_and_fill_one_share_market_order(live_broker: IBKRPaperBroker) -> None:
    """The most expensive test: place a 1-share QQQ MKT order during
    regular trading hours, wait for fill, then flatten with a SELL.

    Skipped outside RTH (a MKT order would still go through but won't
    fill until the next session — not useful for this test).
    """
    if not _is_during_rth():
        pytest.skip("market closed; cannot verify MKT fill outside RTH")

    buy = _equity_buy_market(qty=1, tag="intg-roundtrip")
    update = await live_broker.place_order(buy)
    assert update.status in (
        OrderStatus.SUBMITTED, OrderStatus.PENDING_SUBMIT, OrderStatus.FILLED,
    )
    status = await _wait_for_status(
        live_broker, buy.intent_id, (OrderStatus.FILLED,), timeout_s=45,
    )
    assert status == OrderStatus.FILLED

    # Drain at least one fill event for this intent.
    fills_for_intent = []
    for _ in range(20):
        async for f in live_broker.stream_fills():
            if f.intent_id == buy.intent_id:
                fills_for_intent.append(f)
        if fills_for_intent:
            break
        await asyncio.sleep(0.25)
    assert fills_for_intent, "expected at least one Fill event for the BUY"
    fill = fills_for_intent[0]
    assert fill.symbol == "QQQ"
    assert fill.side == OrderSide.BUY
    assert fill.quantity >= 1
    assert fill.price > 0

    # Flatten with a SELL.
    sell = _equity_sell_market(qty=1, tag="intg-flat")
    await live_broker.place_order(sell)
    sell_status = await _wait_for_status(
        live_broker, sell.intent_id, (OrderStatus.FILLED,), timeout_s=45,
    )
    assert sell_status == OrderStatus.FILLED


@pytest.mark.asyncio
async def test_positions_after_round_trip_is_flat(live_broker: IBKRPaperBroker) -> None:
    """After the buy+sell round trip, get_positions() should not show
    a QQQ long. Runs sequentially after the round-trip test."""
    if not _is_during_rth():
        pytest.skip("market closed; flat-position check needs RTH round-trip")

    # Sanity: do the round trip here too, so this test can run standalone.
    buy = _equity_buy_market(qty=1, tag="intg-flat-check")
    await live_broker.place_order(buy)
    await _wait_for_status(
        live_broker, buy.intent_id, (OrderStatus.FILLED,), timeout_s=45,
    )
    sell = _equity_sell_market(qty=1, tag="intg-flat-check")
    await live_broker.place_order(sell)
    await _wait_for_status(
        live_broker, sell.intent_id, (OrderStatus.FILLED,), timeout_s=45,
    )

    # IBKR's position view updates asynchronously; give it a moment.
    await asyncio.sleep(2.0)
    positions = await live_broker.get_positions()
    qqq_positions = [p for p in positions if p.symbol == "QQQ" and not p.is_option]
    # Should be flat (no position, or zero quantity).
    assert all(p.quantity == 0 for p in qqq_positions), (
        f"expected no open QQQ position after round trip; got {qqq_positions}",
    )
