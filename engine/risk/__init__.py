"""Risk and safety guards for alpha-kite-v2.

Every guard implements ``RiskGuard`` from ``contracts.risk`` and is fail-closed:
unexpected exceptions in ``check`` are converted into BLOCK results.
"""

from __future__ import annotations

from engine.risk.kill_switch import KillSwitchGuard
from engine.risk.limits import (
    DailyLossLimitGuard,
    MaxOpenPositionsGuard,
    MaxPremiumPctNavGuard,
)
from engine.risk.paper_guard import PaperAccountGuard
from engine.risk.pipeline import RiskPipeline

__all__ = [
    "DailyLossLimitGuard",
    "KillSwitchGuard",
    "MaxOpenPositionsGuard",
    "MaxPremiumPctNavGuard",
    "PaperAccountGuard",
    "RiskPipeline",
]
