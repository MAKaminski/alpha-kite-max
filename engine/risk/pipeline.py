"""Composite risk pipeline.

Runs every configured guard, aggregates their reasons, and returns a single
:class:`RiskCheck`. Result is BLOCK if any guard blocks; ALLOW only if all
guards allow. The pipeline itself is fail-closed: an unhandled exception
inside a guard is treated as a BLOCK by that guard (each guard already
handles this internally) and unhandled exceptions inside the pipeline are
likewise translated to BLOCK.
"""

from __future__ import annotations

from datetime import UTC, datetime

from contracts.risk import RiskCheck, RiskDecision, RiskGuard


class RiskPipeline:
    """Sequential composition of :class:`RiskGuard` implementations."""

    name: str = "risk_pipeline"

    def __init__(self, guards: list[RiskGuard]) -> None:
        self._guards: list[RiskGuard] = list(guards)

    @property
    def guards(self) -> list[RiskGuard]:
        return list(self._guards)

    def evaluate(self, **context: object) -> RiskCheck:
        now = datetime.now(tz=UTC)
        block_reasons: list[str] = []
        allow_reasons: list[str] = []

        for guard in self._guards:
            guard_name = getattr(guard, "name", type(guard).__name__)
            try:
                result = guard.check(**context)
            except Exception as exc:
                block_reasons.append(
                    f"guard {guard_name} raised {type(exc).__name__}"
                )
                continue

            if not isinstance(result, RiskCheck):
                block_reasons.append(
                    f"guard {guard_name} returned non-RiskCheck "
                    f"({type(result).__name__}); failing closed"
                )
                continue

            if result.decision == RiskDecision.BLOCK:
                if result.reasons:
                    block_reasons.extend(result.reasons)
                else:
                    block_reasons.append(f"guard {guard_name} blocked (no reason given)")
            elif result.reasons:
                allow_reasons.extend(result.reasons)

        if block_reasons:
            return RiskCheck(
                decision=RiskDecision.BLOCK,
                checked_at=now,
                reasons=block_reasons,
            )
        return RiskCheck(
            decision=RiskDecision.ALLOW,
            checked_at=now,
            reasons=allow_reasons or ["all guards passed"],
        )
