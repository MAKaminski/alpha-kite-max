"""Pure-function technical indicators for the alpha-kite engine.

All indicator functions are stateless, synchronous, and operate on
``Decimal`` values. They are safe to call from any context and never
perform I/O.
"""

from __future__ import annotations

from engine.indicators.cross import cross_events, detect_cross
from engine.indicators.sma import simple_moving_average
from engine.indicators.vwap import session_vwap

__all__ = [
    "cross_events",
    "detect_cross",
    "session_vwap",
    "simple_moving_average",
]
