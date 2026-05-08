"""Series cross detection helpers."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

CrossDirection = Literal["UP", "DOWN", "NONE"]
CrossEvent = Literal["UP", "DOWN"]


def detect_cross(
    prev_a: Decimal | None,
    prev_b: Decimal | None,
    curr_a: Decimal,
    curr_b: Decimal,
) -> CrossDirection:
    """Detect whether series A crossed series B between the previous and current step.

    Returns ``"UP"`` if A was at or below B and is now strictly above,
    ``"DOWN"`` if A was at or above B and is now strictly below, else ``"NONE"``.
    """
    if not isinstance(curr_a, Decimal) or not isinstance(curr_b, Decimal):
        raise TypeError("curr_a and curr_b must be Decimal values")
    if prev_a is None or prev_b is None:
        return "NONE"
    if prev_a <= prev_b and curr_a > curr_b:
        return "UP"
    if prev_a >= prev_b and curr_a < curr_b:
        return "DOWN"
    return "NONE"


def cross_events(
    series_a: list[Decimal | None],
    series_b: list[Decimal | None],
) -> list[tuple[int, CrossEvent]]:
    """Return ``(index, direction)`` tuples for each cross between paired series.

    Indices are positions in the input lists. ``None`` entries are treated as
    "no value yet" — a cross can only be reported once both series have a
    prior and current Decimal value.
    """
    if len(series_a) != len(series_b):
        raise ValueError("series_a and series_b must be the same length")
    events: list[tuple[int, CrossEvent]] = []
    prev_a: Decimal | None = None
    prev_b: Decimal | None = None
    for i, (a, b) in enumerate(zip(series_a, series_b, strict=True)):
        if a is not None and b is not None:
            direction = detect_cross(prev_a, prev_b, a, b)
            if direction != "NONE":
                events.append((i, direction))
            prev_a, prev_b = a, b
        else:
            # Reset previous values; we cannot evaluate a cross with a missing side.
            prev_a, prev_b = None, None
    return events
