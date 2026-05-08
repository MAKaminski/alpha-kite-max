"""Numeric pre-trade risk limits.

Three guards, all fail-closed. Each consumes a typed subset of the
``check`` context kwargs documented on its ``check`` method.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from contracts.broker import AccountSummary, OrderIntent
from contracts.risk import RiskCheck, RiskDecision


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _to_decimal(value: object, name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float, str)):
        return Decimal(str(value))
    raise TypeError(f"{name} must be Decimal/int/float/str, got {type(value).__name__}")


class MaxOpenPositionsGuard:
    """Block when ``open_positions >= max_open``."""

    name: str = "max_open_positions"

    def __init__(self, max_open: int) -> None:
        if max_open < 0:
            raise ValueError("max_open must be >= 0")
        self._max_open: int = int(max_open)

    @property
    def max_open(self) -> int:
        return self._max_open

    def check(self, **context: object) -> RiskCheck:
        now = _now()
        try:
            raw = context.get("open_positions")
            if raw is None:
                return RiskCheck(
                    decision=RiskDecision.BLOCK,
                    checked_at=now,
                    reasons=[f"guard {self.name}: missing 'open_positions' context"],
                )
            open_positions = int(raw)  # type: ignore[arg-type]
            if open_positions >= self._max_open:
                return RiskCheck(
                    decision=RiskDecision.BLOCK,
                    checked_at=now,
                    reasons=[
                        f"guard {self.name}: open_positions={open_positions} "
                        f">= max_open={self._max_open}"
                    ],
                )
            return RiskCheck(
                decision=RiskDecision.ALLOW,
                checked_at=now,
                reasons=[
                    f"guard {self.name}: open_positions={open_positions} "
                    f"< max_open={self._max_open}"
                ],
            )
        except Exception as exc:
            return RiskCheck(
                decision=RiskDecision.BLOCK,
                checked_at=now,
                reasons=[f"guard {self.name} raised {type(exc).__name__}"],
            )


class DailyLossLimitGuard:
    """Block when realized P&L for today is at or below ``-|limit_usd|``."""

    name: str = "daily_loss_limit"

    def __init__(self, limit_usd: Decimal | int | float | str) -> None:
        limit = limit_usd if isinstance(limit_usd, Decimal) else Decimal(str(limit_usd))
        self._limit_usd: Decimal = abs(limit)

    @property
    def limit_usd(self) -> Decimal:
        return self._limit_usd

    def check(self, **context: object) -> RiskCheck:
        now = _now()
        try:
            raw = context.get("realized_pnl_today")
            if raw is None:
                return RiskCheck(
                    decision=RiskDecision.BLOCK,
                    checked_at=now,
                    reasons=[f"guard {self.name}: missing 'realized_pnl_today' context"],
                )
            realized = _to_decimal(raw, "realized_pnl_today")
            threshold = -self._limit_usd
            if realized <= threshold:
                return RiskCheck(
                    decision=RiskDecision.BLOCK,
                    checked_at=now,
                    reasons=[
                        f"guard {self.name}: realized_pnl_today={realized} "
                        f"<= -limit_usd={threshold}"
                    ],
                )
            return RiskCheck(
                decision=RiskDecision.ALLOW,
                checked_at=now,
                reasons=[
                    f"guard {self.name}: realized_pnl_today={realized} "
                    f"> -limit_usd={threshold}"
                ],
            )
        except Exception as exc:
            return RiskCheck(
                decision=RiskDecision.BLOCK,
                checked_at=now,
                reasons=[f"guard {self.name} raised {type(exc).__name__}"],
            )


class MaxPremiumPctNavGuard:
    """Block when proposed premium notional exceeds ``max_pct`` of NAV.

    For options, premium is multiplied by the contract multiplier (default
    100). For equities the multiplier is 1.
    """

    name: str = "max_premium_pct_nav"

    def __init__(self, max_pct: Decimal | int | float | str) -> None:
        max_pct_d = max_pct if isinstance(max_pct, Decimal) else Decimal(str(max_pct))
        if max_pct_d <= 0:
            raise ValueError("max_pct must be > 0 (in percent units, e.g. 0.5 == 0.5%)")
        self._max_pct: Decimal = max_pct_d

    @property
    def max_pct(self) -> Decimal:
        return self._max_pct

    def check(self, **context: object) -> RiskCheck:
        now = _now()
        try:
            intent = context.get("intent")
            account = context.get("account")
            last_premium_raw = context.get("last_premium")

            missing: list[str] = []
            if intent is None:
                missing.append("intent")
            if account is None:
                missing.append("account")
            if last_premium_raw is None:
                missing.append("last_premium")
            if missing:
                return RiskCheck(
                    decision=RiskDecision.BLOCK,
                    checked_at=now,
                    reasons=[f"guard {self.name}: missing context {missing}"],
                )

            if not isinstance(intent, OrderIntent):
                return RiskCheck(
                    decision=RiskDecision.BLOCK,
                    checked_at=now,
                    reasons=[
                        f"guard {self.name}: 'intent' must be OrderIntent, got "
                        f"{type(intent).__name__}"
                    ],
                )
            if not isinstance(account, AccountSummary):
                return RiskCheck(
                    decision=RiskDecision.BLOCK,
                    checked_at=now,
                    reasons=[
                        f"guard {self.name}: 'account' must be AccountSummary, got "
                        f"{type(account).__name__}"
                    ],
                )

            last_premium = _to_decimal(last_premium_raw, "last_premium")
            qty = Decimal(intent.quantity)
            if intent.is_option and intent.option is not None:
                multiplier = Decimal(intent.option.multiplier)
            elif intent.is_option:
                multiplier = Decimal(100)
            else:
                multiplier = Decimal(1)

            notional = last_premium * qty * multiplier
            nav = Decimal(account.net_liquidation)
            if nav <= 0:
                return RiskCheck(
                    decision=RiskDecision.BLOCK,
                    checked_at=now,
                    reasons=[
                        f"guard {self.name}: net_liquidation={nav} <= 0; "
                        f"cannot evaluate premium ratio"
                    ],
                )

            cap = (self._max_pct / Decimal(100)) * nav
            if notional > cap:
                return RiskCheck(
                    decision=RiskDecision.BLOCK,
                    checked_at=now,
                    reasons=[
                        f"guard {self.name}: notional={notional} > cap={cap} "
                        f"(max_pct={self._max_pct}% of NAV={nav})"
                    ],
                )
            return RiskCheck(
                decision=RiskDecision.ALLOW,
                checked_at=now,
                reasons=[
                    f"guard {self.name}: notional={notional} <= cap={cap} "
                    f"(max_pct={self._max_pct}% of NAV={nav})"
                ],
            )
        except Exception as exc:
            return RiskCheck(
                decision=RiskDecision.BLOCK,
                checked_at=now,
                reasons=[f"guard {self.name} raised {type(exc).__name__}"],
            )
