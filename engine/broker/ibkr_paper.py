"""IBKR paper-trading broker gateway.

Wraps `ib_insync.IB` with a fail-closed paper-account guard. Live accounts are
refused unless `dry_run=True` (which short-circuits anything that would talk
to the real broker).

Account is considered "paper" if any of:
  * account id contains a case-insensitive substring from the allowlist
  * account id starts with "DU" (IB's paper-account convention)
  * any AccountType / AccountCode tag contains "PAPER" or "DEMO"
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator, Iterable
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
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
    TimeInForce,
)
from contracts.data_feed import OptionContract

from engine.broker.base import AbstractBroker
from engine.broker.dry_run import DryRunBroker
from engine.broker.errors import (
    NonPaperAccountError,
    NotConnectedError,
    OrderRejectedError,
)

logger = logging.getLogger(__name__)


_PAPER_PREFIX = "DU"  # IB convention for paper-trading accounts (e.g. DU1234567)
_PAPER_TAG_TOKENS = ("PAPER", "DEMO")
_ACCOUNT_TYPE_TAGS = ("AccountType", "AccountCode")

_IBKR_STATUS_MAP: dict[str, OrderStatus] = {
    "PendingSubmit": OrderStatus.PENDING_SUBMIT,
    "PendingCancel": OrderStatus.PENDING_SUBMIT,
    "PreSubmitted": OrderStatus.SUBMITTED,
    "Submitted": OrderStatus.SUBMITTED,
    "ApiCancelled": OrderStatus.CANCELLED,
    "Cancelled": OrderStatus.CANCELLED,
    "Filled": OrderStatus.FILLED,
    "Inactive": OrderStatus.REJECTED,
}


class IBKRPaperBroker(AbstractBroker):
    """BrokerGateway implementation backed by ib_insync, restricted to paper.

    The constructor does NOT connect; call `await broker.connect()` first. The
    paper-account guard runs in `connect()` after `accountSummary()` is
    available, so a live account never even gets the chance to receive an
    order intent (unless `dry_run=True`, in which case we route to an internal
    DryRunBroker and never call `placeOrder`).
    """

    name = "ibkr_paper"

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 17,
        dry_run: bool = True,
        paper_account_allowlist: Iterable[str] | None = None,
        ib: Any | None = None,
    ) -> None:
        super().__init__(dry_run=dry_run)
        self.host = host
        self.port = int(port)
        self.client_id = int(client_id)
        self.paper_account_allowlist: list[str] = list(
            paper_account_allowlist if paper_account_allowlist is not None else ("DEMO", "PAPER")
        )

        # Lazy-import ib_insync so non-IBKR test suites don't have to depend
        # on a running IB Gateway.
        if ib is None:
            from ib_insync import IB  # type: ignore[import-not-found]

            ib = IB()
        self.ib = ib

        self._dry_run_inner: DryRunBroker | None = None
        self._account_id: str | None = None
        self._account_type: AccountType = AccountType.UNKNOWN
        self._account_summary_cache: list[Any] = []

        # Maps for translating intent_id <-> ib_insync.Trade
        self._trades_by_intent: dict[UUID, Any] = {}

        self._order_updates: asyncio.Queue[OrderUpdate] = asyncio.Queue()
        self._fill_queue: asyncio.Queue[Fill] = asyncio.Queue()

        # Reverse-map: ib_insync orderId -> intent_id (filled when we place).
        self._intent_by_order_id: dict[int, UUID] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def connect(self) -> None:
        connect = getattr(self.ib, "connectAsync", None)
        if connect is None:  # pragma: no cover - defensive
            raise BrokerError("ib object lacks connectAsync")  # type: ignore[name-defined]

        result = connect(self.host, self.port, clientId=self.client_id)
        if asyncio.iscoroutine(result):
            await result

        try:
            # ib_insync's sync ``accountSummary()`` calls ``util.run`` which
            # tries to spin up its own event loop — that conflicts with the
            # asyncio loop we're already in and raises
            # "This event loop is already running". Use the async variant
            # so we cooperate with the current loop. The fake _FakeIB used
            # by unit tests returns a plain list from its sync method, so
            # we accept either shape.
            summary_call = getattr(self.ib, "accountSummaryAsync", None)
            if summary_call is None:
                summary = self.ib.accountSummary()
            else:
                summary = summary_call()
            if asyncio.iscoroutine(summary):
                summary = await summary
        except Exception as exc:  # pragma: no cover - depends on IB
            logger.exception("ibkr accountSummary() failed")
            raise NotConnectedError(f"could not fetch accountSummary: {exc}") from exc

        self._account_summary_cache = list(summary or [])
        self._account_id = self._extract_account_id(self._account_summary_cache)
        self._account_type = self._classify_account_type(self._account_summary_cache)

        # In dry_run we never call placeOrder against the live broker, so the
        # paper guard does not need to fire even if the connected account is
        # live.
        if self.dry_run:
            self._dry_run_inner = DryRunBroker(
                account_id=self._account_id or "DRYRUN-IBKR-0001",
            )
            await self._dry_run_inner.connect()
        else:
            self._enforce_paper_guard(self._account_id, self._account_summary_cache)

        # Wire up event bridges (no-op if events are missing — useful for tests).
        self._wire_events()

        self._connected = True
        self._audit(
            "ibkr.connect",
            {
                "host": self.host,
                "port": self.port,
                "client_id": self.client_id,
                "account_id": self._account_id,
                "account_type": self._account_type.value,
                "dry_run": self.dry_run,
            },
        )

    async def disconnect(self) -> None:
        if self._dry_run_inner is not None:
            await self._dry_run_inner.disconnect()
            self._dry_run_inner = None
        try:
            disconnect = getattr(self.ib, "disconnect", None)
            if disconnect is not None:
                result = disconnect()
                if asyncio.iscoroutine(result):  # pragma: no cover - defensive
                    await result
        finally:
            self._connected = False
            self._audit("ibkr.disconnect", None)

    # ------------------------------------------------------------------
    # Paper-account guard
    # ------------------------------------------------------------------
    def _enforce_paper_guard(
        self, account_id: str | None, summary: list[Any]
    ) -> None:
        """Refuse to operate if we cannot positively identify a paper account."""
        if self._is_paper_account(account_id, summary):
            return
        raise NonPaperAccountError(
            f"refusing to start: account_id={account_id!r} does not match "
            f"paper allowlist {self.paper_account_allowlist!r}; "
            "set dry_run=True to use the in-memory simulator instead."
        )

    def _is_paper_account(self, account_id: str | None, summary: list[Any]) -> bool:
        # 1) DU* convention
        if account_id and account_id.upper().startswith(_PAPER_PREFIX):
            return True

        # 2) Allowlist substring match against the account id
        if account_id:
            haystack = account_id.lower()
            for needle in self.paper_account_allowlist:
                if needle and needle.lower() in haystack:
                    return True

        # 3) AccountType / AccountCode tag inspection
        for row in summary:
            tag = self._row_attr(row, "tag", "")
            value = self._row_attr(row, "value", "")
            if tag in _ACCOUNT_TYPE_TAGS:
                upper_value = str(value).upper()
                if any(tok in upper_value for tok in _PAPER_TAG_TOKENS):
                    return True
                # Allowlist substring match against the AccountType value
                for needle in self.paper_account_allowlist:
                    if needle and needle.lower() in str(value).lower():
                        return True
        return False

    @staticmethod
    def _row_attr(row: Any, name: str, default: Any = None) -> Any:
        if isinstance(row, dict):
            return row.get(name, default)
        return getattr(row, name, default)

    @classmethod
    def _extract_account_id(cls, summary: list[Any]) -> str | None:
        for row in summary:
            account = cls._row_attr(row, "account", "")
            if account:
                return str(account)
        return None

    @classmethod
    def _classify_account_type(cls, summary: list[Any]) -> AccountType:
        # 1) The DU* account-id convention is the most reliable signal IBKR
        #    gives us. Real paper accounts always start with DU (or DUM in
        #    newer testbeds like DUM428671). The AccountType tag for a paper
        #    account is often the parent account's type ("INDIVIDUAL",
        #    "JOINT", etc.) which by itself would mis-classify as LIVE, so
        #    we check the id prefix first.
        account_id = cls._extract_account_id(summary) or ""
        if account_id.upper().startswith(_PAPER_PREFIX):
            return AccountType.PAPER

        # 2) Otherwise consult the AccountType / AccountCode tags.
        for row in summary:
            tag = cls._row_attr(row, "tag", "")
            value = str(cls._row_attr(row, "value", "")).upper()
            if tag in _ACCOUNT_TYPE_TAGS:
                if "PAPER" in value or "DEMO" in value:
                    return AccountType.PAPER
                if value:
                    if value in {"INDIVIDUAL", "JOINT", "TRUST", "IRA", "CORP", "LIVE"}:
                        return AccountType.LIVE
                    return AccountType.LIVE
        return AccountType.UNKNOWN

    # ------------------------------------------------------------------
    # Account / positions
    # ------------------------------------------------------------------
    async def get_account_summary(self) -> AccountSummary:
        self._assert_connected()
        if self._dry_run_inner is not None:
            inner = await self._dry_run_inner.get_account_summary()
            # Override the account id with the real one if known.
            return inner.model_copy(
                update={"account_id": self._account_id or inner.account_id}
            )

        # See note in connect() — prefer the async variant.
        summary_call = getattr(self.ib, "accountSummaryAsync", None)
        if summary_call is None:
            summary = self.ib.accountSummary()
        else:
            summary = summary_call()
        if asyncio.iscoroutine(summary):
            summary = await summary
        rows = list(summary or [])

        cash = self._tag_value(rows, "TotalCashValue") or Decimal("0")
        bp = self._tag_value(rows, "BuyingPower") or Decimal("0")
        nav = self._tag_value(rows, "NetLiquidation") or Decimal("0")
        realized = self._tag_value(rows, "RealizedPnL") or Decimal("0")
        unrealized = self._tag_value(rows, "UnrealizedPnL") or Decimal("0")

        return AccountSummary(
            account_id=self._account_id or self._extract_account_id(rows) or "UNKNOWN",
            account_type=self._account_type,
            cash=cash,
            buying_power=bp,
            net_liquidation=nav,
            realized_pnl_today=realized,
            unrealized_pnl=unrealized,
            fetched_at=datetime.now(tz=UTC),
        )

    @classmethod
    def _tag_value(cls, rows: list[Any], tag: str) -> Decimal | None:
        for row in rows:
            if cls._row_attr(row, "tag", "") == tag:
                value = cls._row_attr(row, "value", "")
                try:
                    return Decimal(str(value))
                except (InvalidOperation, ValueError):
                    return None
        return None

    async def get_positions(self) -> list[Position]:
        self._assert_connected()
        if self._dry_run_inner is not None:
            return await self._dry_run_inner.get_positions()

        ib_positions = self.ib.positions() or []
        out: list[Position] = []
        for p in ib_positions:
            contract = getattr(p, "contract", None)
            if contract is None:
                continue
            sec_type = getattr(contract, "secType", "STK")
            qty = int(getattr(p, "position", 0) or 0)
            avg_cost = Decimal(str(getattr(p, "avgCost", 0) or 0))
            if sec_type == "OPT":
                option = OptionContract(
                    underlying=getattr(contract, "symbol", ""),
                    expiry=_parse_ib_expiry(getattr(contract, "lastTradeDateOrContractMonth", "")),
                    strike=Decimal(str(getattr(contract, "strike", 0) or 0)),
                    right="C" if getattr(contract, "right", "C") == "C" else "P",
                    multiplier=int(getattr(contract, "multiplier", 100) or 100),
                    exchange=getattr(contract, "exchange", "SMART") or "SMART",
                )
                out.append(
                    Position(
                        symbol=getattr(contract, "symbol", ""),
                        is_option=True,
                        option=option,
                        quantity=qty,
                        avg_cost=avg_cost,
                    )
                )
            else:
                out.append(
                    Position(
                        symbol=getattr(contract, "symbol", ""),
                        is_option=False,
                        option=None,
                        quantity=qty,
                        avg_cost=avg_cost,
                    )
                )
        return out

    # ------------------------------------------------------------------
    # Order entry
    # ------------------------------------------------------------------
    async def place_order(self, intent: OrderIntent) -> OrderUpdate:
        self._assert_connected()
        if self._dry_run_inner is not None:
            self._audit(
                "ibkr.place_order.dry_run",
                {
                    "intent_id": str(intent.intent_id),
                    "symbol": intent.symbol,
                    "side": intent.side.value,
                    "qty": intent.quantity,
                    "type": intent.order_type.value,
                },
            )
            update = await self._dry_run_inner.place_order(intent)
            # Re-broadcast onto our own queues so callers using THIS broker's
            # streams see them.
            self._order_updates.put_nowait(update)
            async for fill in self._dry_run_inner.stream_fills():
                self._fill_queue.put_nowait(fill)
            return update

        # Live (paper) submission path.
        contract = self._build_ib_contract(intent)
        order = self._build_ib_order(intent)

        try:
            trade = self.ib.placeOrder(contract, order)
        except Exception as exc:  # pragma: no cover - depends on IB
            raise OrderRejectedError(str(exc)) from exc

        broker_order_id = str(getattr(getattr(trade, "order", None), "orderId", "") or "")
        self._trades_by_intent[intent.intent_id] = trade
        if broker_order_id:
            try:
                self._intent_by_order_id[int(broker_order_id)] = intent.intent_id
            except (TypeError, ValueError):
                pass

        self._audit(
            "ibkr.place_order",
            {
                "intent_id": str(intent.intent_id),
                "broker_order_id": broker_order_id,
                "symbol": intent.symbol,
                "side": intent.side.value,
                "qty": intent.quantity,
                "type": intent.order_type.value,
            },
        )

        status = self._translate_status(getattr(getattr(trade, "orderStatus", None), "status", ""))
        return OrderUpdate(
            intent_id=intent.intent_id,
            broker_order_id=broker_order_id or "",
            status=status,
            timestamp=datetime.now(tz=UTC),
            filled_qty=int(getattr(getattr(trade, "orderStatus", None), "filled", 0) or 0),
            avg_fill_price=_decimal_or_none(
                getattr(getattr(trade, "orderStatus", None), "avgFillPrice", None)
            ),
            reason=None,
        )

    async def cancel_order(self, intent_id: UUID) -> OrderUpdate:
        self._assert_connected()
        if self._dry_run_inner is not None:
            update = await self._dry_run_inner.cancel_order(intent_id)
            self._order_updates.put_nowait(update)
            return update

        trade = self._trades_by_intent.get(intent_id)
        if trade is None:
            raise OrderRejectedError(
                f"unknown intent_id {intent_id}; cannot cancel an order we did not place"
            )
        self.ib.cancelOrder(getattr(trade, "order", trade))
        broker_order_id = str(getattr(getattr(trade, "order", None), "orderId", "") or "")
        return OrderUpdate(
            intent_id=intent_id,
            broker_order_id=broker_order_id,
            status=OrderStatus.PENDING_SUBMIT,
            timestamp=datetime.now(tz=UTC),
            filled_qty=int(getattr(getattr(trade, "orderStatus", None), "filled", 0) or 0),
            avg_fill_price=_decimal_or_none(
                getattr(getattr(trade, "orderStatus", None), "avgFillPrice", None)
            ),
            reason="cancel requested",
        )

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
    # ib_insync event wiring
    # ------------------------------------------------------------------
    def _wire_events(self) -> None:
        order_event = getattr(self.ib, "orderStatusEvent", None)
        if order_event is not None and hasattr(order_event, "__iadd__"):
            try:
                order_event += self._on_order_status  # type: ignore[operator]
            except Exception:  # pragma: no cover - defensive
                logger.debug("could not subscribe to orderStatusEvent")

        exec_event = getattr(self.ib, "execDetailsEvent", None)
        if exec_event is not None and hasattr(exec_event, "__iadd__"):
            try:
                exec_event += self._on_exec_details  # type: ignore[operator]
            except Exception:  # pragma: no cover - defensive
                logger.debug("could not subscribe to execDetailsEvent")

    def _on_order_status(self, trade: Any) -> None:
        order = getattr(trade, "order", None)
        order_id = int(getattr(order, "orderId", 0) or 0)
        intent_id = self._intent_by_order_id.get(order_id)
        if intent_id is None:
            return
        status = getattr(getattr(trade, "orderStatus", None), "status", "")
        update = OrderUpdate(
            intent_id=intent_id,
            broker_order_id=str(order_id),
            status=self._translate_status(status),
            timestamp=datetime.now(tz=UTC),
            filled_qty=int(getattr(getattr(trade, "orderStatus", None), "filled", 0) or 0),
            avg_fill_price=_decimal_or_none(
                getattr(getattr(trade, "orderStatus", None), "avgFillPrice", None)
            ),
            reason=None,
        )
        self._order_updates.put_nowait(update)

    def _on_exec_details(self, trade: Any, fill: Any) -> None:
        order = getattr(trade, "order", None)
        order_id = int(getattr(order, "orderId", 0) or 0)
        intent_id = self._intent_by_order_id.get(order_id)
        if intent_id is None:
            return
        contract = getattr(trade, "contract", None) or getattr(fill, "contract", None)
        execution = getattr(fill, "execution", fill)
        commission_report = getattr(fill, "commissionReport", None)
        commission = Decimal(
            str(getattr(commission_report, "commission", 0) or 0)
        )
        side = OrderSide.BUY if str(getattr(execution, "side", "BOT")).upper().startswith("B") else OrderSide.SELL
        symbol = getattr(contract, "symbol", "") or ""
        sec_type = getattr(contract, "secType", "STK")
        option_obj: OptionContract | None = None
        if sec_type == "OPT" and contract is not None:
            option_obj = OptionContract(
                underlying=symbol,
                expiry=_parse_ib_expiry(getattr(contract, "lastTradeDateOrContractMonth", "")),
                strike=Decimal(str(getattr(contract, "strike", 0) or 0)),
                right="C" if getattr(contract, "right", "C") == "C" else "P",
                multiplier=int(getattr(contract, "multiplier", 100) or 100),
                exchange=getattr(contract, "exchange", "SMART") or "SMART",
            )
        out_fill = Fill(
            fill_id=str(getattr(execution, "execId", uuid.uuid4().hex)),
            intent_id=intent_id,
            broker_order_id=str(order_id),
            timestamp=datetime.now(tz=UTC),
            symbol=symbol,
            is_option=sec_type == "OPT",
            option=option_obj,
            side=side,
            quantity=int(getattr(execution, "shares", 0) or 0),
            price=Decimal(str(getattr(execution, "price", 0) or 0)),
            commission=commission,
        )
        self._fill_queue.put_nowait(out_fill)

    # ------------------------------------------------------------------
    # ib_insync object construction
    # ------------------------------------------------------------------
    @staticmethod
    def _translate_status(raw: str) -> OrderStatus:
        return _IBKR_STATUS_MAP.get(str(raw or ""), OrderStatus.SUBMITTED)

    def _build_ib_contract(self, intent: OrderIntent) -> Any:
        from ib_insync import Option, Stock  # type: ignore[import-not-found]

        if intent.is_option and intent.option is not None:
            opt = intent.option
            return Option(
                symbol=opt.underlying,
                lastTradeDateOrContractMonth=opt.expiry.strftime("%Y%m%d"),
                strike=float(opt.strike),
                right=opt.right,
                exchange=opt.exchange or "SMART",
                multiplier=str(opt.multiplier),
            )
        return Stock(intent.symbol, "SMART", "USD")

    def _build_ib_order(self, intent: OrderIntent) -> Any:
        from ib_insync import LimitOrder, MarketOrder  # type: ignore[import-not-found]

        action = "BUY" if intent.side == OrderSide.BUY else "SELL"
        tif = _tif_to_ib(intent.time_in_force)
        if intent.order_type == OrderType.LIMIT and intent.limit_price is not None:
            order = LimitOrder(action, intent.quantity, float(intent.limit_price))
        else:
            order = MarketOrder(action, intent.quantity)
        order.tif = tif
        return order


# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------
def _tif_to_ib(tif: TimeInForce) -> str:
    return {
        TimeInForce.DAY: "DAY",
        TimeInForce.GTC: "GTC",
        TimeInForce.IOC: "IOC",
    }[tif]


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if d == 0:
        return None
    return d


def _parse_ib_expiry(raw: str):
    from datetime import date

    s = str(raw or "")
    if len(s) >= 8 and s[:8].isdigit():
        return date(int(s[0:4]), int(s[4:6]), int(s[6:8]))
    # Fallback: today (best-effort; positions reconciliation only).
    return date(1970, 1, 1)


# Keep BrokerError available if subclasses want it without re-importing.
from engine.broker.errors import BrokerError  # noqa: E402  (re-export)

__all__ = ["IBKRPaperBroker"]
