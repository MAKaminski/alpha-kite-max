"""Tests for numeric pre-trade risk limits."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from contracts.broker import (
    AccountSummary,
    AccountType,
    OrderIntent,
    OrderSide,
    OrderType,
)
from contracts.data_feed import OptionContract
from contracts.risk import RiskDecision
from engine.risk.limits import (
    DailyLossLimitGuard,
    MaxOpenPositionsGuard,
    MaxPremiumPctNavGuard,
)


def _account(nav: Decimal | int = 5000) -> AccountSummary:
    return AccountSummary(
        account_id="DU123",
        account_type=AccountType.PAPER,
        cash=Decimal(str(nav)),
        buying_power=Decimal(str(nav)),
        net_liquidation=Decimal(str(nav)),
        fetched_at=datetime.now(tz=UTC),
    )


def _option_intent(quantity: int = 1) -> OrderIntent:
    return OrderIntent(
        intent_id=uuid4(),
        created_at=datetime.now(tz=UTC),
        symbol="QQQ",
        is_option=True,
        option=OptionContract(
            underlying="QQQ",
            expiry=date(2026, 5, 15),
            strike=Decimal("400"),
            right="C",
            multiplier=100,
        ),
        side=OrderSide.BUY,
        quantity=quantity,
        order_type=OrderType.MARKET,
    )


# ---------------------------------------------------------------------------
# MaxOpenPositionsGuard
# ---------------------------------------------------------------------------


def test_max_open_positions_block_at_limit() -> None:
    guard = MaxOpenPositionsGuard(1)
    result = guard.check(open_positions=1)
    assert result.decision == RiskDecision.BLOCK
    assert not result.allowed


def test_max_open_positions_allow_below_limit() -> None:
    guard = MaxOpenPositionsGuard(2)
    result = guard.check(open_positions=1)
    assert result.decision == RiskDecision.ALLOW


def test_max_open_positions_block_above_limit() -> None:
    guard = MaxOpenPositionsGuard(1)
    result = guard.check(open_positions=5)
    assert result.decision == RiskDecision.BLOCK


def test_max_open_positions_missing_context_blocks() -> None:
    guard = MaxOpenPositionsGuard(1)
    result = guard.check()
    assert result.decision == RiskDecision.BLOCK


def test_max_open_positions_zero_max_blocks_anything() -> None:
    guard = MaxOpenPositionsGuard(0)
    assert guard.check(open_positions=0).decision == RiskDecision.BLOCK


def test_max_open_positions_rejects_negative_max() -> None:
    with pytest.raises(ValueError):
        MaxOpenPositionsGuard(-1)


# ---------------------------------------------------------------------------
# DailyLossLimitGuard
# ---------------------------------------------------------------------------


def test_daily_loss_block_at_threshold() -> None:
    guard = DailyLossLimitGuard(Decimal("50"))
    result = guard.check(realized_pnl_today=Decimal("-50"))
    assert result.decision == RiskDecision.BLOCK


def test_daily_loss_allow_just_above_threshold() -> None:
    guard = DailyLossLimitGuard(Decimal("50"))
    result = guard.check(realized_pnl_today=Decimal("-49.99"))
    assert result.decision == RiskDecision.ALLOW


def test_daily_loss_block_below_threshold() -> None:
    guard = DailyLossLimitGuard(Decimal("50"))
    result = guard.check(realized_pnl_today=Decimal("-100"))
    assert result.decision == RiskDecision.BLOCK


def test_daily_loss_allow_when_pnl_positive() -> None:
    guard = DailyLossLimitGuard(Decimal("50"))
    result = guard.check(realized_pnl_today=Decimal("123.45"))
    assert result.decision == RiskDecision.ALLOW


def test_daily_loss_accepts_int_input() -> None:
    guard = DailyLossLimitGuard(50)
    assert guard.check(realized_pnl_today=-49).decision == RiskDecision.ALLOW
    assert guard.check(realized_pnl_today=-50).decision == RiskDecision.BLOCK


def test_daily_loss_handles_signed_limit() -> None:
    # Operator could pass a negative limit; we use abs().
    guard = DailyLossLimitGuard(Decimal("-50"))
    assert guard.limit_usd == Decimal("50")
    assert guard.check(realized_pnl_today=Decimal("-50")).decision == RiskDecision.BLOCK


def test_daily_loss_missing_context_blocks() -> None:
    guard = DailyLossLimitGuard(Decimal("50"))
    assert guard.check().decision == RiskDecision.BLOCK


# ---------------------------------------------------------------------------
# MaxPremiumPctNavGuard
# ---------------------------------------------------------------------------


def test_max_premium_pct_blocks_when_notional_exceeds_cap() -> None:
    # premium 1.10 * 1 contract * 100 multiplier = $110
    # cap = 0.5% of $5000 = $25  ->  $110 > $25 => BLOCK
    guard = MaxPremiumPctNavGuard(Decimal("0.5"))
    result = guard.check(
        intent=_option_intent(quantity=1),
        account=_account(nav=5000),
        last_premium=Decimal("1.10"),
    )
    assert result.decision == RiskDecision.BLOCK


def test_max_premium_pct_allows_when_notional_within_cap() -> None:
    # cap = 5% of $5000 = $250; notional $110 -> ALLOW
    guard = MaxPremiumPctNavGuard(Decimal("5"))
    result = guard.check(
        intent=_option_intent(quantity=1),
        account=_account(nav=5000),
        last_premium=Decimal("1.10"),
    )
    assert result.decision == RiskDecision.ALLOW


def test_max_premium_pct_uses_quantity() -> None:
    # 0.10 * 5 contracts * 100 = $50; NAV $5000; cap 0.5% = $25 -> BLOCK
    guard = MaxPremiumPctNavGuard(Decimal("0.5"))
    result = guard.check(
        intent=_option_intent(quantity=5),
        account=_account(nav=5000),
        last_premium=Decimal("0.10"),
    )
    assert result.decision == RiskDecision.BLOCK


def test_max_premium_pct_zero_nav_blocks() -> None:
    guard = MaxPremiumPctNavGuard(Decimal("0.5"))
    result = guard.check(
        intent=_option_intent(),
        account=_account(nav=0),
        last_premium=Decimal("0.10"),
    )
    assert result.decision == RiskDecision.BLOCK


def test_max_premium_pct_missing_context_blocks() -> None:
    guard = MaxPremiumPctNavGuard(Decimal("0.5"))
    assert guard.check().decision == RiskDecision.BLOCK


def test_max_premium_pct_equity_uses_multiplier_one() -> None:
    intent = OrderIntent(
        intent_id=uuid4(),
        created_at=datetime.now(tz=UTC),
        symbol="QQQ",
        is_option=False,
        side=OrderSide.BUY,
        quantity=10,
        order_type=OrderType.MARKET,
    )
    # 10 shares * $20 = $200 notional; cap 5% of $5000 = $250 -> ALLOW
    guard = MaxPremiumPctNavGuard(Decimal("5"))
    assert (
        guard.check(intent=intent, account=_account(nav=5000), last_premium=Decimal("20")).decision
        == RiskDecision.ALLOW
    )


def test_max_premium_pct_invalid_constructor() -> None:
    with pytest.raises(ValueError):
        MaxPremiumPctNavGuard(Decimal("0"))


def test_max_premium_pct_wrong_intent_type_blocks() -> None:
    guard = MaxPremiumPctNavGuard(Decimal("0.5"))
    result = guard.check(
        intent="not-an-intent",
        account=_account(),
        last_premium=Decimal("1"),
    )
    assert result.decision == RiskDecision.BLOCK
