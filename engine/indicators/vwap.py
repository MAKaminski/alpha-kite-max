"""Session VWAP indicator computed from OHLCV bars."""

from __future__ import annotations

from decimal import Decimal

from contracts.data_feed import Bar

_THREE = Decimal(3)


def session_vwap(bars: list[Bar]) -> Decimal | None:
    """Return cumulative VWAP from typical price ``(H+L+C)/3`` weighted by volume.

    Returns ``None`` on empty input or when total volume is zero.
    Resetting on a session boundary is the caller's responsibility.
    """
    if not bars:
        return None
    pv_total = Decimal(0)
    vol_total = 0
    for bar in bars:
        if bar.volume < 0:
            raise ValueError("bar volume must be non-negative")
        typical = (bar.high + bar.low + bar.close) / _THREE
        pv_total += typical * Decimal(bar.volume)
        vol_total += bar.volume
    if vol_total == 0:
        return None
    return pv_total / Decimal(vol_total)
