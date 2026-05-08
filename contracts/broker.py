"""Broker gateway contract.

The strategy engine never imports a broker SDK directly. It emits OrderIntent
objects and hands them to a BrokerGateway implementation. The gateway is the
ONLY component allowed to call IBKR's placeOrder.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from contracts.data_feed import OptionContract, OptionRight


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MKT"
    LIMIT = "LMT"


class TimeInForce(str, Enum):
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"


class OrderStatus(str, Enum):
    PENDING_SUBMIT = "PENDING_SUBMIT"
    SUBMITTED = "SUBMITTED"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class AccountType(str, Enum):
    PAPER = "PAPER"
    DEMO = "DEMO"
    LIVE = "LIVE"
    UNKNOWN = "UNKNOWN"


class OrderIntent(_Frozen):
    """A trade the strategy wants placed. Strategy emits these; broker translates
    them into broker-native orders."""

    intent_id: UUID
    created_at: datetime
    symbol: str  # underlying for options
    is_option: bool
    option: OptionContract | None = None
    side: OrderSide
    quantity: int
    order_type: OrderType
    limit_price: Decimal | None = None
    time_in_force: TimeInForce = TimeInForce.DAY
    tag: str = Field(default="", description="Free-form tag, persisted to audit log")

    def model_post_init(self, __context) -> None:  # type: ignore[override]
        if self.is_option and self.option is None:
            raise ValueError("OrderIntent.is_option=True requires .option to be set")
        if self.order_type == OrderType.LIMIT and self.limit_price is None:
            raise ValueError("OrderIntent.order_type=LIMIT requires .limit_price")


class Fill(_Frozen):
    """Single execution leg returned by the broker."""

    fill_id: str
    intent_id: UUID
    broker_order_id: str
    timestamp: datetime
    symbol: str
    is_option: bool
    option: OptionContract | None = None
    side: OrderSide
    quantity: int
    price: Decimal
    commission: Decimal = Decimal("0")


class Position(_Frozen):
    """Currently held position as reported by broker reconciliation."""

    symbol: str
    is_option: bool
    option: OptionContract | None = None
    quantity: int
    avg_cost: Decimal
    market_value: Decimal | None = None
    unrealized_pnl: Decimal | None = None


class AccountSummary(_Frozen):
    """Account state for pre-trade checks and the daily-loss guard."""

    account_id: str
    account_type: AccountType
    cash: Decimal
    buying_power: Decimal
    net_liquidation: Decimal
    realized_pnl_today: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    fetched_at: datetime


class OrderUpdate(_Frozen):
    """Async order status update streamed from broker."""

    intent_id: UUID
    broker_order_id: str
    status: OrderStatus
    timestamp: datetime
    filled_qty: int = 0
    avg_fill_price: Decimal | None = None
    reason: str | None = None


@runtime_checkable
class BrokerGateway(Protocol):
    """The only component allowed to call broker.placeOrder.

    Implementations are expected to:
      * Refuse to start if account_type is not in the paper allowlist (when
        the engine is configured for paper mode).
      * Convert OrderIntent → broker-native order.
      * Yield OrderUpdate / Fill events as they arrive.
      * Honor `dry_run`: persist the OrderIntent to audit log but never call
        the broker's placeOrder.
    """

    name: str
    dry_run: bool

    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...

    async def get_account_summary(self) -> AccountSummary: ...
    async def get_positions(self) -> list[Position]: ...

    async def place_order(self, intent: OrderIntent) -> OrderUpdate: ...
    async def cancel_order(self, intent_id: UUID) -> OrderUpdate: ...

    async def stream_order_updates(self):  # AsyncIterator[OrderUpdate]
        ...

    async def stream_fills(self):  # AsyncIterator[Fill]
        ...


__all__ = [
    "AccountSummary",
    "AccountType",
    "BrokerGateway",
    "Fill",
    "OptionContract",
    "OptionRight",
    "OrderIntent",
    "OrderSide",
    "OrderStatus",
    "OrderType",
    "OrderUpdate",
    "Position",
    "TimeInForce",
]
