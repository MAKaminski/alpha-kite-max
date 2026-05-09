"""PersistenceWriter — write events to the configured storage backend.

All methods are async and idempotent on conflict (UPSERTs land cleanly
even if the same intent / fill / position is written twice).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from contracts.broker import Fill, OrderIntent, Position
from contracts.data_feed import Bar, Quote
from contracts.strategy import Signal

from services.persistence.models import AuditEvent
from services.persistence.storage import StorageBackend


def _dec_str(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _option_fields(option: Any | None) -> dict[str, Any]:
    """Flatten an OptionContract into the (expiry, strike, right) row columns."""
    if option is None:
        return {
            "option_expiry": None,
            "option_strike": None,
            "option_right": None,
        }
    return {
        "option_expiry": option.expiry,
        "option_strike": _dec_str(option.strike),
        "option_right": option.right,
    }


class PersistenceWriter:
    """Write market data, signals, intents, fills, positions, audit, and P&L."""

    def __init__(self, backend: StorageBackend) -> None:
        self._backend = backend

    # ── market data ──────────────────────────────────────────────────────

    async def write_tick(self, quote: Quote, feed: str) -> None:
        row = {
            "symbol": quote.symbol,
            "ts": quote.timestamp,
            "bid": _dec_str(quote.bid),
            "ask": _dec_str(quote.ask),
            "last": _dec_str(quote.last),
            "volume": quote.volume,
            "feed": feed,
        }
        await self._backend.insert("ticks", [row])

    async def write_bar(self, bar: Bar, feed: str) -> None:
        await self.write_bars([bar], feed)

    async def write_bars(self, bars: list[Bar], feed: str) -> None:
        """Bulk-write bars in a single batched upsert.

        Use this from any caller that has more than a handful of bars to
        persist (e.g. ``scripts/backfill_bars.py``). The writer hands every
        row to ``backend.upsert`` which then collapses them into 500-row
        multi-row INSERTs — orders of magnitude faster than one upsert per
        bar over the public internet.
        """
        if not bars:
            return
        rows = [
            {
                "symbol": b.symbol,
                "interval_seconds": b.interval_seconds,
                "open_time": b.open_time,
                "open": _dec_str(b.open),
                "high": _dec_str(b.high),
                "low": _dec_str(b.low),
                "close": _dec_str(b.close),
                "volume": b.volume,
                "vwap": _dec_str(b.vwap),
                "feed": feed,
            }
            for b in bars
        ]
        await self._backend.upsert(
            "bars",
            rows,
            conflict_columns=["symbol", "interval_seconds", "open_time"],
        )

    # ── strategy signals ─────────────────────────────────────────────────

    async def write_signal(self, signal: Signal) -> None:
        row = {
            "strategy": signal.name,
            "symbol": signal.symbol,
            "direction": signal.direction.value,
            "ts": signal.timestamp,
            "strength": _dec_str(signal.strength),
            "metadata": dict(signal.metadata),
        }
        await self._backend.insert("signals", [row])

    # ── orders / fills / positions ───────────────────────────────────────

    async def write_order_intent(self, intent: OrderIntent, dry_run: bool) -> None:
        row = {
            "intent_id": str(intent.intent_id),
            "created_at": intent.created_at,
            "symbol": intent.symbol,
            "is_option": intent.is_option,
            **_option_fields(intent.option),
            "side": intent.side.value,
            "quantity": intent.quantity,
            "order_type": intent.order_type.value,
            "limit_price": _dec_str(intent.limit_price),
            "time_in_force": intent.time_in_force.value,
            "dry_run": dry_run,
            "tag": intent.tag,
        }
        await self._backend.upsert(
            "order_intents", [row], conflict_columns=["intent_id"]
        )

    async def write_fill(self, fill: Fill) -> None:
        row = {
            "fill_id": fill.fill_id,
            "intent_id": str(fill.intent_id),
            "broker_order_id": fill.broker_order_id,
            "ts": fill.timestamp,
            "symbol": fill.symbol,
            "is_option": fill.is_option,
            **_option_fields(fill.option),
            "side": fill.side.value,
            "quantity": fill.quantity,
            "price": _dec_str(fill.price),
            "commission": _dec_str(fill.commission),
        }
        await self._backend.upsert("fills", [row], conflict_columns=["fill_id"])

    async def write_position(self, position: Position) -> None:
        row = {
            "symbol": position.symbol,
            "is_option": position.is_option,
            **_option_fields(position.option),
            "quantity": position.quantity,
            "avg_cost": _dec_str(position.avg_cost),
            "market_value": _dec_str(position.market_value),
            "unrealized_pnl": _dec_str(position.unrealized_pnl),
        }
        await self._backend.upsert(
            "positions",
            [row],
            conflict_columns=[
                "symbol",
                "is_option",
                "option_expiry",
                "option_strike",
                "option_right",
            ],
        )

    # ── audit log ────────────────────────────────────────────────────────

    async def write_audit(self, event: AuditEvent) -> None:
        row = {
            "ts": event.ts,
            "actor": event.actor,
            "event_type": event.event_type,
            "severity": event.severity,
            "message": event.message,
            "payload": dict(event.payload),
        }
        await self._backend.insert("audit_log", [row])

    # ── daily P&L roll-up ────────────────────────────────────────────────

    async def bump_daily_pnl(
        self,
        trading_day: date,
        realized_delta: Decimal,
        win: bool | None,
    ) -> None:
        """Increment realized P&L and trade counters for `trading_day`.

        - `realized_delta` is added to `realized_usd`.
        - `trades` always +1.
        - `wins` += 1 when `win is True`; `losses` += 1 when `win is False`;
          neither is bumped when `win is None`.
        """
        existing = await self._backend.select(
            "daily_pnl", where={"trading_day": trading_day}, limit=1
        )

        if existing:
            current = existing[0]
            cur_realized = Decimal(str(current.get("realized_usd", "0") or "0"))
            cur_unrealized = Decimal(str(current.get("unrealized_usd", "0") or "0"))
            cur_trades = int(current.get("trades", 0) or 0)
            cur_wins = int(current.get("wins", 0) or 0)
            cur_losses = int(current.get("losses", 0) or 0)
        else:
            cur_realized = Decimal("0")
            cur_unrealized = Decimal("0")
            cur_trades = 0
            cur_wins = 0
            cur_losses = 0

        new_realized = cur_realized + realized_delta
        new_trades = cur_trades + 1
        new_wins = cur_wins + (1 if win is True else 0)
        new_losses = cur_losses + (1 if win is False else 0)

        row = {
            "trading_day": trading_day,
            "realized_usd": str(new_realized),
            "unrealized_usd": str(cur_unrealized),
            "trades": new_trades,
            "wins": new_wins,
            "losses": new_losses,
        }
        await self._backend.upsert(
            "daily_pnl", [row], conflict_columns=["trading_day"]
        )


__all__ = ["PersistenceWriter"]
