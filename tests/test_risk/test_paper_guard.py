"""Tests for the paper-account guard."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from contracts.broker import AccountSummary, AccountType
from contracts.risk import RiskDecision
from engine.risk.paper_guard import PaperAccountGuard


def _account(account_id: str, account_type: AccountType) -> AccountSummary:
    return AccountSummary(
        account_id=account_id,
        account_type=account_type,
        cash=Decimal("10000"),
        buying_power=Decimal("10000"),
        net_liquidation=Decimal("10000"),
        fetched_at=datetime.now(tz=UTC),
    )


def test_paper_account_type_is_allowed() -> None:
    guard = PaperAccountGuard(allowlist=["DEMO", "PAPER"])
    account = _account("U1", AccountType.PAPER)
    result = guard.check(account=account)
    assert result.decision == RiskDecision.ALLOW
    assert result.allowed


def test_du_prefix_is_allowed_even_when_account_type_says_live() -> None:
    # IBKR paper account ids always start with DU; trust the prefix.
    guard = PaperAccountGuard(allowlist=["DEMO", "PAPER"])
    account = _account("DU123", AccountType.LIVE)
    result = guard.check(account=account)
    assert result.decision == RiskDecision.ALLOW


def test_live_account_with_no_match_is_blocked() -> None:
    guard = PaperAccountGuard(allowlist=["DEMO", "PAPER"])
    account = _account("U1234567", AccountType.LIVE)
    result = guard.check(account=account)
    assert result.decision == RiskDecision.BLOCK
    assert not result.allowed
    assert result.reasons


def test_demo_account_type_with_explicit_allowlist() -> None:
    guard = PaperAccountGuard(allowlist=["DEMO", "PAPER"])
    account = _account("DEMO-42", AccountType.DEMO)
    result = guard.check(account=account)
    assert result.decision == RiskDecision.ALLOW


def test_allowlist_substring_case_insensitive() -> None:
    guard = PaperAccountGuard(allowlist=["paper"])
    account = _account("MyPAPERacct", AccountType.LIVE)
    result = guard.check(account=account)
    assert result.decision == RiskDecision.ALLOW


def test_required_mode_live_is_no_op() -> None:
    guard = PaperAccountGuard(allowlist=[], required_mode="live")
    account = _account("U1234567", AccountType.LIVE)
    result = guard.check(account=account)
    assert result.decision == RiskDecision.ALLOW


def test_unknown_account_type_no_match_blocks() -> None:
    guard = PaperAccountGuard(allowlist=["PAPER"])
    account = _account("X9", AccountType.UNKNOWN)
    result = guard.check(account=account)
    assert result.decision == RiskDecision.BLOCK


def test_missing_account_blocks() -> None:
    guard = PaperAccountGuard(allowlist=["PAPER"])
    result = guard.check()
    assert result.decision == RiskDecision.BLOCK


def test_wrong_type_blocks() -> None:
    guard = PaperAccountGuard(allowlist=["PAPER"])
    result = guard.check(account="not-an-account")
    assert result.decision == RiskDecision.BLOCK


def test_du_lowercase_still_matches() -> None:
    guard = PaperAccountGuard(allowlist=[])
    account = _account("du42", AccountType.LIVE)
    result = guard.check(account=account)
    assert result.decision == RiskDecision.ALLOW
