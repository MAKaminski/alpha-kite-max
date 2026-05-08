"""On-disk kill-switch sentinel guard.

If the configured sentinel file exists at ``check`` time, every order is
blocked. Operators can engage the kill switch by ``touch``-ing the file and
release it by deleting it. Content of the file is irrelevant.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from contracts.risk import KillSwitchState, RiskCheck, RiskDecision


class KillSwitchGuard:
    """Fail-closed file-presence guard."""

    name: str = "kill_switch"

    def __init__(self, sentinel_path: str | Path) -> None:
        self._sentinel_path: Path = Path(sentinel_path)

    @property
    def sentinel_path(self) -> Path:
        return self._sentinel_path

    def state(self) -> KillSwitchState:
        engaged = self._sentinel_path.exists()
        return KillSwitchState(
            engaged=engaged,
            sentinel_path=str(self._sentinel_path),
            detected_at=datetime.now(tz=UTC),
            note="sentinel present" if engaged else "sentinel absent",
        )

    def check(self, **context: object) -> RiskCheck:
        now = datetime.now(tz=UTC)
        try:
            engaged = self._sentinel_path.exists()
        except Exception as exc:  # pragma: no cover - defensive, fail closed
            return RiskCheck(
                decision=RiskDecision.BLOCK,
                checked_at=now,
                reasons=[f"guard {self.name} raised {type(exc).__name__}"],
            )

        if engaged:
            return RiskCheck(
                decision=RiskDecision.BLOCK,
                checked_at=now,
                reasons=[f"kill switch engaged: sentinel exists at {self._sentinel_path}"],
            )
        return RiskCheck(
            decision=RiskDecision.ALLOW,
            checked_at=now,
            reasons=[f"kill switch not engaged ({self._sentinel_path})"],
        )
