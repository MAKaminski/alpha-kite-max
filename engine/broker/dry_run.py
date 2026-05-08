"""In-memory dry-run broker.

The `DryRunBroker` never touches the network. It records every order intent,
synthesizes an immediate FILLED OrderUpdate at the intent's limit price (or a
fixed `1.00` for market orders), and updates an in-memory position book. It is
the default broker when running tests, replays, or any "what-if" simulation.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from contracts.broker import (
    AccountSummary,
    AccountType,
    Fill,
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    OrderUpdate,
    Position,
)

from engine.broker.base import AbstractBroker

logger = logging.getLogger(__name__)


_DEFAULT_FAKE_ACCOUNT_ID = "DRYRUN-PAPER-0001"
_DEFAULT_FAKE_NAV = Decimal("5000")
_DEFAULT_MKT_FILL_PRICE = Decimal("1.00")


class DryRunBroker(AbstractBroker):
    """A broker gateway that fills every order in memory.

    Round-trip flow:
      1. `connect()` flips `_connected = True`.
      2. `place_order(intent)` records the intent, synthesizes a Fill at
         `intent.limit_price` (or `1.00` for MKT), updates positions, and
         pushes the OrderUpdate + Fill to internal asyncio queues.
      3. `stream_order_updates()` / `stream_fills()` drain the queues.
    """

    name = "dry_run"

    def __init__(
        self,
        account_id: str = _DEFAULT_FAKE_ACCOUNT_ID,
        starting_nav: Decimal = _DEFAULT_FAKE_NAV,
    ) -> None:
        super().__init__(dry_run=True)
        self._account_id = account_id
        self._nav = starting_nav

        self._intents: dict[UUID, OrderIntent] = {}
        self._fills: list[Fill] = []
        self._positions: dict[tuple[str, str | None], Position] = {}

        self._order_updates: asyncio.Queue[OrderUpdate] = asyncio.Queue()
        self._fill_queue: asyncio.Queue[Fill] = asyncio.Queue()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def connect(self) -> None:
        self._connected = True
        self._audit("dry_run.connect", {"account_id": self._account_id})

    async def disconnect(self) -> None:
        self._connected = False
        self._audit("dry_run.disconnect", None)

    # ------------------------------------------------------------------
    # Account / positions
    # ------------------------------------------------------------------
    async def get_account_summary(self) -> AccountSummary:
        self._assert_connected()
        return AccountSummary(
            account_id=self._account_id,
            account_type=AccountType.PAPER,
            cash=self._nav,
            buying_power=self._nav,
            net_liquidation=self._nav,
            fetched_at=datetime.now(tz=UTC),
        )

    async def get_positions(self) -> list[Position]:
        self._assert_connected()
        return [p for p in self._positions.values() if p.quantity != 0]

    # ------------------------------------------------------------------
    # Order entry
    # ------------------------------------------------------------------
    async def place_order(self, intent: OrderIntent) -> OrderUpdate:
        self._assert_connected()
        self._intents[intent.intent_id] = intent
        self._audit(
            "dry_run.place_order",
            {
                "intent_id": str(intent.intent_id),
                "symbol": intent.symbol,
                "side": intent.side.value,
                "qty": intent.quantity,
                "type": intent.order_type.value,
            },
        )

        price = self._fill_price(intent)
        broker_order_id = f"DRY-{intent.intent_id.hex[:8]}"
        now = datetime.now(tz=UTC)

        fill = Fill(
            fill_id=f"DRYFILL-{uuid.uuid4().hex[:10]}",
            intent_id=intent.intent_id,
            broker_order_id=broker_order_id,
            timestamp=now,
            symbol=intent.symbol,
            is_option=intent.is_option,
            option=intent.option,
            side=intent.side,
            quantity=intent.quantity,
            price=price,
            commission=Decimal("0"),
        )
        self._record_fill(fill)

        update = OrderUpdate(
            intent_id=intent.intent_id,
            broker_order_id=broker_order_id,
            status=OrderStatus.FILLED,
            timestamp=now,
            filled_qty=intent.quantity,
            avg_fill_price=price,
            reason=None,
        )
        self._order_updates.put_nowait(update)
        self._fill_queue.put_nowait(fill)

        return update

    async def cancel_order(self, intent_id: UUID) -> OrderUpdate:
        self._assert_connected()
        self._audit("dry_run.cancel_order", {"intent_id": str(intent_id)})
        update = OrderUpdate(
            intent_id=intent_id,
            broker_order_id=f"DRY-{intent_id.hex[:8]}",
            status=OrderStatus.CANCELLED,
            timestamp=datetime.now(tz=UTC),
            filled_qty=0,
            avg_fill_price=None,
            reason="dry_run cancel",
        )
        self._order_updates.put_nowait(update)
        return update

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------
    async def stream_order_updates(self) -> AsyncIterator[OrderUpdate]:
        self._assert_connected()
        while True:
            try:
                update = self._order_updates.get_nowait()
            except asyncio.QueueEmpty:
                return
            yield update

    async def stream_fills(self) -> AsyncIterator[Fill]:
        self._assert_connected()
        while True:
            try:
                fill = self._fill_queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            yield fill

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    @staticmethod
    def _fill_price(intent: OrderIntent) -> Decimal:
        if intent.order_type == OrderType.LIMIT and intent.limit_price is not None:
            return Decimal(intent.limit_price)
        return _DEFAULT_MKT_FILL_PRICE

    def _record_fill(self, fill: Fill) -> None:
        self._fills.append(fill)
        key = self._position_key(fill.symbol, fill.option)
        prior = self._positions.get(key)

        signed_qty = fill.quantity if fill.side == OrderSide.BUY else -fill.quantity
        if prior is None:
            new_qty = signed_qty
            new_avg_cost = fill.price
        else:
            new_qty = prior.quantity + signed_qty
            if (prior.quantity >= 0 and signed_qty >= 0) or (
                prior.quantity <= 0 and signed_qty <= 0
            ):
                # Same-direction add: weighted average.
                if new_qty == 0:
                    new_avg_cost = prior.avg_cost
                else:
                    total_cost = prior.avg_cost * Decimal(abs(prior.quantity)) + (
                        fill.price * Decimal(abs(signed_qty))
                    )
                    new_avg_cost = total_cost / Decimal(abs(new_qty))
            else:
                # Reducing or flipping: keep the original cost basis until flat.
                new_avg_cost = prior.avg_cost if new_qty != 0 else Decimal("0")

        self._positions[key] = Position(
            symbol=fill.symbol,
            is_option=fill.is_option,
            option=fill.option,
            quantity=new_qty,
            avg_cost=new_avg_cost,
            market_value=None,
            unrealized_pnl=None,
        )

    @staticmethod
    def _position_key(
        symbol: str, option
    ) -> tuple[str, str | None]:
        if option is None:
            return (symbol, None)
        token = f"{option.underlying}|{option.expiry.isoformat()}|{option.strike}|{option.right}"
        return (symbol, token)


__all__ = ["DryRunBroker"]
