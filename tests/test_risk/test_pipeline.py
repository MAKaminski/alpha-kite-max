"""Tests for the composite risk pipeline."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from contracts.broker import (
    AccountSummary,
    AccountType,
    OrderIntent,
    OrderSide,
    OrderType,
)
from contracts.data_feed import OptionContract
from contracts.risk import RiskCheck, RiskDecision
from engine.risk.kill_switch import KillSwitchGuard
from engine.risk.limits import (
    DailyLossLimitGuard,
    MaxOpenPositionsGuard,
    MaxPremiumPctNavGuard,
)
from engine.risk.paper_guard import PaperAccountGuard
from engine.risk.pipeline import RiskPipeline


def _intent() -> OrderIntent:
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
        ),
        side=OrderSide.BUY,
        quantity=1,
        order_type=OrderType.MARKET,
    )


def _account(account_id: str = "DU123", account_type: AccountType = AccountType.PAPER) -> AccountSummary:
    return AccountSummary(
        account_id=account_id,
        account_type=account_type,
        cash=Decimal("100000"),
        buying_power=Decimal("100000"),
        net_liquidation=Decimal("100000"),
        fetched_at=datetime.now(tz=UTC),
    )


def _build_pipeline(sentinel: Path) -> RiskPipeline:
    return RiskPipeline(
        guards=[
            KillSwitchGuard(sentinel),
            MaxOpenPositionsGuard(2),
            DailyLossLimitGuard(Decimal("50")),
            MaxPremiumPctNavGuard(Decimal("5")),
            PaperAccountGuard(allowlist=["DEMO", "PAPER"]),
        ]
    )


def test_pipeline_allows_when_all_pass(tmp_path: Path) -> None:
    pipeline = _build_pipeline(tmp_path / "KILL")
    result = pipeline.evaluate(
        intent=_intent(),
        account=_account(),
        open_positions=0,
        realized_pnl_today=Decimal("0"),
        last_premium=Decimal("0.50"),
    )
    assert result.decision == RiskDecision.ALLOW
    assert result.allowed
    assert result.reasons


def test_pipeline_fails_closed_on_kill_switch(tmp_path: Path) -> None:
    sentinel = tmp_path / "KILL"
    sentinel.touch()
    pipeline = _build_pipeline(sentinel)
    result = pipeline.evaluate(
        intent=_intent(),
        account=_account(),
        open_positions=0,
        realized_pnl_today=Decimal("0"),
        last_premium=Decimal("0.50"),
    )
    assert result.decision == RiskDecision.BLOCK
    assert any("kill switch" in r for r in result.reasons)


def test_pipeline_blocks_on_max_positions(tmp_path: Path) -> None:
    pipeline = _build_pipeline(tmp_path / "KILL")
    result = pipeline.evaluate(
        intent=_intent(),
        account=_account(),
        open_positions=2,
        realized_pnl_today=Decimal("0"),
        last_premium=Decimal("0.50"),
    )
    assert result.decision == RiskDecision.BLOCK
    assert any("max_open_positions" in r for r in result.reasons)


def test_pipeline_blocks_on_daily_loss(tmp_path: Path) -> None:
    pipeline = _build_pipeline(tmp_path / "KILL")
    result = pipeline.evaluate(
        intent=_intent(),
        account=_account(),
        open_positions=0,
        realized_pnl_today=Decimal("-100"),
        last_premium=Decimal("0.50"),
    )
    assert result.decision == RiskDecision.BLOCK
    assert any("daily_loss_limit" in r for r in result.reasons)


def test_pipeline_blocks_on_paper_guard(tmp_path: Path) -> None:
    pipeline = _build_pipeline(tmp_path / "KILL")
    result = pipeline.evaluate(
        intent=_intent(),
        account=_account(account_id="U7654321", account_type=AccountType.LIVE),
        open_positions=0,
        realized_pnl_today=Decimal("0"),
        last_premium=Decimal("0.50"),
    )
    assert result.decision == RiskDecision.BLOCK
    assert any("paper_account" in r for r in result.reasons)


def test_pipeline_aggregates_multiple_block_reasons(tmp_path: Path) -> None:
    sentinel = tmp_path / "KILL"
    sentinel.touch()
    pipeline = _build_pipeline(sentinel)
    result = pipeline.evaluate(
        intent=_intent(),
        account=_account(account_id="U7654321", account_type=AccountType.LIVE),
        open_positions=99,
        realized_pnl_today=Decimal("-9999"),
        last_premium=Decimal("0.50"),
    )
    assert result.decision == RiskDecision.BLOCK
    # Multiple guards must contribute reasons.
    assert len(result.reasons) >= 2


def test_pipeline_treats_guard_exception_as_block(tmp_path: Path) -> None:
    class _Boom:
        name = "boom"

        def check(self, **context: object) -> RiskCheck:  # type: ignore[override]
            raise RuntimeError("kaboom")

    pipeline = RiskPipeline(guards=[_Boom()])
    result = pipeline.evaluate()
    assert result.decision == RiskDecision.BLOCK
    assert any("boom" in r and "RuntimeError" in r for r in result.reasons)


def test_pipeline_empty_allows() -> None:
    pipeline = RiskPipeline(guards=[])
    result = pipeline.evaluate()
    assert result.decision == RiskDecision.ALLOW
    assert result.reasons == ["all guards passed"]


def test_pipeline_blocks_on_premium_cap(tmp_path: Path) -> None:
    # Build a pipeline with a tighter premium cap to trigger block.
    pipeline = RiskPipeline(
        guards=[
            KillSwitchGuard(tmp_path / "KILL"),
            MaxPremiumPctNavGuard(Decimal("0.01")),  # 0.01% cap
            PaperAccountGuard(allowlist=["DEMO", "PAPER"]),
        ]
    )
    result = pipeline.evaluate(
        intent=_intent(),
        account=_account(),
        last_premium=Decimal("1.00"),
    )
    assert result.decision == RiskDecision.BLOCK
    assert any("max_premium_pct_nav" in r for r in result.reasons)
