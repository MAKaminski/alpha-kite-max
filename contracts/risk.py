"""Risk and safety contract."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class RiskDecision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


class RiskCheck(_Frozen):
    """Result of one or more risk checks against a proposed OrderIntent."""

    decision: RiskDecision
    checked_at: datetime
    reasons: list[str]

    @property
    def allowed(self) -> bool:
        return self.decision == RiskDecision.ALLOW


class KillSwitchState(_Frozen):
    """Current state of the on-disk kill switch sentinel."""

    engaged: bool
    sentinel_path: str
    detected_at: datetime
    note: str | None = None


class DailyLossState(_Frozen):
    """Realized P&L state for the current trading day."""

    trading_day: str  # ISO date
    realized_pnl_usd: Decimal
    limit_usd: Decimal
    breached: bool


class RiskGuard(Protocol):
    """A pre-trade check. Implementations: paper-mode guard, daily-loss guard,
    max-open-positions guard, kill-switch guard."""

    name: str

    def check(self, **context) -> RiskCheck: ...
