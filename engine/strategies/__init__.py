"""Strategy implementations for the alpha-kite-v2 engine.

Each strategy is a class that satisfies the :class:`contracts.strategy.Strategy`
Protocol. Strategies are pure decision-making components: they consume a
:class:`StrategyContext` and emit :class:`StrategyDecision` objects containing
:class:`Signal` and :class:`OrderIntent` records. They never call brokers,
data feeds, or persistence layers directly.
"""

from __future__ import annotations

from engine.strategies.buy_vol_qqq_cross import BuyVolQQQCrossStrategy
from engine.strategies.buy_vol_qqq_cross_tick import BuyVolQQQCrossTickStrategy
from engine.strategies.sell_put_qqq_cross import (
    SellPutQQQCrossStrategy,
    TakeProfitTier,
    default_tiers,
)

__all__ = [
    "BuyVolQQQCrossStrategy",
    "BuyVolQQQCrossTickStrategy",
    "SellPutQQQCrossStrategy",
    "TakeProfitTier",
    "default_tiers",
]
