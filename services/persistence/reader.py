"""PersistenceReader — read from the configured storage backend.

Used by the dashboard and by ad-hoc operator tooling. All methods are
async so they work uniformly across the in-memory and Postgres backends.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from services.persistence.models import DailyPnlRow
from services.persistence.storage import StorageBackend

_SEVERITY_ORDER = {"INFO": 0, "WARN": 1, "ERROR": 2}


def _coerce_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError(f"cannot coerce {value!r} to date")


def _coerce_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class PersistenceReader:
    """Read recent signals, open positions, daily P&L, and audit entries."""

    def __init__(self, backend: StorageBackend) -> None:
        self._backend = backend

    async def recent_signals(self, limit: int = 100) -> list[dict[str, Any]]:
        return await self._backend.select(
            "signals", order_by="ts DESC", limit=limit
        )

    async def open_positions(self) -> list[dict[str, Any]]:
        rows = await self._backend.select("positions")
        return [r for r in rows if int(r.get("quantity", 0) or 0) != 0]

    async def daily_pnl(self, days: int = 30) -> list[DailyPnlRow]:
        rows = await self._backend.select(
            "daily_pnl", order_by="trading_day DESC", limit=days
        )
        cutoff = date.today() - timedelta(days=days)
        out: list[DailyPnlRow] = []
        for r in rows:
            day = _coerce_date(r["trading_day"])
            if day < cutoff:
                continue
            out.append(
                DailyPnlRow(
                    trading_day=day,
                    realized_usd=_coerce_decimal(r.get("realized_usd")),
                    unrealized_usd=_coerce_decimal(r.get("unrealized_usd")),
                    trades=int(r.get("trades", 0) or 0),
                    wins=int(r.get("wins", 0) or 0),
                    losses=int(r.get("losses", 0) or 0),
                )
            )
        return out

    async def recent_audit(
        self,
        limit: int = 200,
        severity_min: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = await self._backend.select(
            "audit_log", order_by="ts DESC", limit=limit
        )
        if severity_min is None:
            return rows
        threshold = _SEVERITY_ORDER.get(severity_min.upper())
        if threshold is None:
            return rows
        return [
            r
            for r in rows
            if _SEVERITY_ORDER.get(str(r.get("severity", "INFO")).upper(), 0)
            >= threshold
        ]


__all__ = ["PersistenceReader"]
