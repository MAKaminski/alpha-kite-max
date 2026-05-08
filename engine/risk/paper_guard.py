"""Paper-account guard.

Refuses to authorize orders against accounts that don't look like
paper/demo accounts when the engine is configured for paper mode.
``required_mode == "live"`` is a no-op; broker rails enforce live-mode
gating elsewhere (and v1 of alpha-kite-v2 disallows live mode at config
load time anyway).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from contracts.broker import AccountSummary, AccountType
from contracts.risk import RiskCheck, RiskDecision


class PaperAccountGuard:
    """Allow only paper / demo accounts (or explicitly allow-listed ids)."""

    name: str = "paper_account"

    def __init__(
        self,
        allowlist: list[str],
        required_mode: Literal["paper", "live"] = "paper",
    ) -> None:
        self._allowlist: list[str] = [s.strip() for s in allowlist if s and s.strip()]
        self._required_mode: Literal["paper", "live"] = required_mode

    @property
    def allowlist(self) -> list[str]:
        return list(self._allowlist)

    @property
    def required_mode(self) -> Literal["paper", "live"]:
        return self._required_mode

    def check(self, **context: object) -> RiskCheck:
        now = datetime.now(tz=UTC)
        try:
            account = context.get("account")
            if account is None:
                return RiskCheck(
                    decision=RiskDecision.BLOCK,
                    checked_at=now,
                    reasons=[f"guard {self.name}: missing 'account' context"],
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

            if self._required_mode == "live":
                return RiskCheck(
                    decision=RiskDecision.ALLOW,
                    checked_at=now,
                    reasons=[f"guard {self.name}: live mode (delegated)"],
                )

            account_id = account.account_id or ""
            account_id_upper = account_id.upper()

            # Paper / Demo account types are intrinsically allowed.
            if account.account_type in (AccountType.PAPER, AccountType.DEMO):
                return RiskCheck(
                    decision=RiskDecision.ALLOW,
                    checked_at=now,
                    reasons=[
                        f"guard {self.name}: account_type={account.account_type.value}"
                    ],
                )

            # IBKR paper accounts always begin with "DU".
            if account_id_upper.startswith("DU"):
                return RiskCheck(
                    decision=RiskDecision.ALLOW,
                    checked_at=now,
                    reasons=[
                        f"guard {self.name}: account_id '{account_id}' starts with DU"
                    ],
                )

            # Operator-specified allowlist substrings (case-insensitive).
            for needle in self._allowlist:
                if needle.upper() in account_id_upper:
                    return RiskCheck(
                        decision=RiskDecision.ALLOW,
                        checked_at=now,
                        reasons=[
                            f"guard {self.name}: account_id '{account_id}' "
                            f"matches allowlist entry '{needle}'"
                        ],
                    )

            return RiskCheck(
                decision=RiskDecision.BLOCK,
                checked_at=now,
                reasons=[
                    f"guard {self.name}: account '{account_id}' "
                    f"(type={account.account_type.value}) is not paper/demo "
                    f"and not in allowlist {self._allowlist}"
                ],
            )
        except Exception as exc:
            return RiskCheck(
                decision=RiskDecision.BLOCK,
                checked_at=now,
                reasons=[f"guard {self.name} raised {type(exc).__name__}"],
            )
