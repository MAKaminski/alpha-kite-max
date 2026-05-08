"""Small dataclasses for things not already covered by `contracts/`.

`contracts/` owns the wire types that strategies, brokers, and feeds
exchange. This module owns the few extra row-shaped objects the
persistence layer cares about (audit events, daily P&L roll-ups).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    """A single safety-critical event written to `audit_log`."""

    ts: datetime
    actor: str
    event_type: str
    severity: str
    message: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DailyPnlRow:
    """A single day's P&L roll-up as returned by the reader."""

    trading_day: date
    realized_usd: Decimal
    unrealized_usd: Decimal
    trades: int
    wins: int
    losses: int


__all__ = ["AuditEvent", "DailyPnlRow"]
