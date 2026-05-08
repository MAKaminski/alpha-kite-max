"""Strategy contract.

A Strategy consumes Bars or Quotes (ticks) and (optionally) OptionQuotes
through StrategyContext and emits Signal + OrderIntent. It MUST NOT touch a
BrokerGateway directly; the orchestrator is responsible for sending
OrderIntents to the broker after risk checks pass.

Strategies declare their `kind` so the orchestrator knows which loop to use.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from contracts.broker import OrderIntent
from contracts.data_feed import Bar, OptionQuote, Quote


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


StrategyKind = Literal["bar", "tick"]


class SignalDirection(str, Enum):
    LONG_VOL_UP = "LONG_VOL_UP"  # SMA crossed above VWAP → long vol via call (or straddle)
    LONG_VOL_DOWN = "LONG_VOL_DOWN"  # SMA crossed below VWAP → long vol via put (or straddle)
    EXIT = "EXIT"
    NONE = "NONE"


class Signal(_Frozen):
    """A discrete event emitted by a Strategy."""

    name: str
    direction: SignalDirection
    timestamp: datetime
    symbol: str
    strength: Decimal = Decimal("1")
    metadata: dict[str, str] = Field(default_factory=dict)


class StrategyContext(_Frozen):
    """Per-event view of the world the Strategy receives.

    Bar-driven strategies populate `last_bar` / `bar_history`.
    Tick-driven strategies populate `last_tick` / `tick_history`.
    Both may receive `option_quotes` for entry pricing or exit triggers.
    """

    now: datetime
    last_bar: Bar | None = None
    bar_history: list[Bar] = Field(default_factory=list)
    last_tick: Quote | None = None
    tick_history: list[Quote] = Field(default_factory=list)
    option_quotes: list[OptionQuote] = Field(default_factory=list)
    open_positions: int = 0
    cash_available: Decimal = Decimal("0")


class StrategyDecision(_Frozen):
    """What the Strategy returns each event: zero or more signals + intents."""

    signals: list[Signal] = Field(default_factory=list)
    intents: list[OrderIntent] = Field(default_factory=list)


@runtime_checkable
class Strategy(Protocol):
    """Pluggable strategy. Stateless from the orchestrator's POV — strategies
    may keep internal state but must derive everything they need from
    StrategyContext arguments.

    `kind` determines which event loop the orchestrator runs:
      * "bar"  — orchestrator iterates feed.stream_equity_bars and calls on_bar
      * "tick" — orchestrator iterates feed.stream_equity_quotes and calls on_tick
    Strategies should still return a `StrategyDecision()` from the inactive
    callbacks (they're allowed to be no-ops)."""

    name: str
    kind: StrategyKind

    def on_bar(self, ctx: StrategyContext) -> StrategyDecision:
        """Called once per bar close. No-op for tick strategies."""
        ...

    def on_tick(self, ctx: StrategyContext) -> StrategyDecision:
        """Called on every NBBO tick. No-op for bar strategies."""
        ...

    def on_option_quote(self, ctx: StrategyContext) -> StrategyDecision:
        """Called when a held-position option quote updates (drives exits)."""
        ...

