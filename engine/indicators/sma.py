"""Simple moving average indicator."""

from __future__ import annotations

from decimal import Decimal


def simple_moving_average(closes: list[Decimal], period: int) -> Decimal | None:
    """Return the simple moving average of the trailing ``period`` closes.

    Returns ``None`` until at least ``period`` samples are available.
    """
    if period <= 0:
        raise ValueError("period must be a positive integer")
    if not isinstance(period, int):
        raise TypeError("period must be an int")
    n = len(closes)
    if n < period:
        return None
    window = closes[n - period :]
    total = Decimal(0)
    for value in window:
        if not isinstance(value, Decimal):
            raise TypeError("closes must contain Decimal values")
        total += value
    return total / Decimal(period)
