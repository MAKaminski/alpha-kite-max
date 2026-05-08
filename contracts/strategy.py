"""Strategy contract.

A Strategy consumes Bars + (optionally) OptionQuotes through StrategyContext and
emits Signal + OrderIntent. It MUST NOT touch a BrokerGateway directly; the
orchestrator is responsible for sending OrderIntents to the broker after risk
checks pass.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from contracts.broker import OrderIntent
from contracts.data_feed import Bar, OptionQuote


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SignalDirection(str, Enum):
    LONG_VOL_UP = "LONG_VOL_UP"  # SMA9 crossed above VWAP → long vol via call (or straddle)
    LONG_VOL_DOWN = "LONG_VOL_DOWN"  # SMA9 crossed below VWAP → long vol via put (or straddle)
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
    """Per-tick view of the world the Strategy receives."""

    now: datetime
    last_bar: Bar | None
    bar_history: list[Bar] = Field(default_factory=list)
    option_quotes: list[OptionQuote] = Field(default_factory=list)
    open_positions: int = 0
    cash_available: Decimal = Decimal("0")


class StrategyDecision(_Frozen):
    """What the Strategy returns each tick: zero or more signals + intents."""

    signals: list[Signal] = Field(default_factory=list)
    intents: list[OrderIntent] = Field(default_factory=list)


@runtime_checkable
class Strategy(Protocol):
    """Pluggable strategy. Stateless from the orchestrator's POV — strategies
    may keep internal state but must derive everything they need from
    StrategyContext arguments."""

    name: str

    def on_bar(self, ctx: StrategyContext) -> StrategyDecision:
        """Called once per bar close."""
        ...

    def on_option_quote(self, ctx: StrategyContext) -> StrategyDecision:
        """Called when a held-position option quote updates (drives exits)."""
        ...
