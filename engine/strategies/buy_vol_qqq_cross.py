"""Buy-volatility QQQ SMA9/VWAP cross strategy.

The strategy consumes 1-minute bars and emits long-vol entries (call,
put, or straddle) when the SMA(N) of bar closes crosses the bar's session
VWAP. Exits are driven by ``on_option_quote`` ticks: profit target, stop
loss, or a time stop ahead of the session close.

The implementation is fully self-contained and deterministic: every clock
read flows through ``ctx.now`` and every random identifier flows through
``uuid.uuid4`` so callers can monkeypatch it for snapshot tests.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import Literal

from contracts.broker import OrderIntent, OrderSide, OrderType
from contracts.data_feed import Bar, OptionContract, OptionQuote
from contracts.strategy import (
    Signal,
    SignalDirection,
    StrategyContext,
    StrategyDecision,
)


def _sma(closes: list[Decimal], period: int) -> Decimal | None:
    """Local trailing simple moving average — keeps the strategy parallelizable.

    Returns ``None`` when there are fewer than ``period`` samples.
    """

    if period <= 0:
        raise ValueError("period must be positive")
    if len(closes) < period:
        return None
    window = closes[-period:]
    return sum(window, Decimal(0)) / Decimal(period)


def _session_vwap(buffer: list[Bar]) -> Decimal | None:
    """Cumulative session VWAP from a bar buffer (typical-price weighted)."""

    if not buffer:
        return None
    weighted = Decimal(0)
    volume = Decimal(0)
    for bar in buffer:
        typical = (bar.high + bar.low + bar.close) / Decimal(3)
        v = Decimal(bar.volume)
        weighted += typical * v
        volume += v
    if volume == 0:
        return None
    return weighted / volume


def _bar_vwap(bar: Bar, buffer: list[Bar]) -> Decimal | None:
    """Prefer the broker-supplied bar VWAP; else compute the session VWAP."""

    if bar.vwap is not None:
        return bar.vwap
    return _session_vwap(buffer)


class _OpenLeg:
    """Internal record for an option leg the strategy considers held."""

    __slots__ = ("contract", "entry_intent_id", "entry_mid", "entry_time", "quantity")

    def __init__(
        self,
        contract: OptionContract,
        quantity: int,
        entry_mid: Decimal,
        entry_intent_id: uuid.UUID,
        entry_time: datetime,
    ) -> None:
        self.contract = contract
        self.quantity = quantity
        self.entry_mid = entry_mid
        self.entry_intent_id = entry_intent_id
        self.entry_time = entry_time


class BuyVolQQQCrossStrategy:
    """SMA9/VWAP cross long-vol strategy implementing the Strategy Protocol."""

    name: str = "buy_vol_qqq_cross"
    kind: str = "bar"

    def on_tick(self, ctx):
        """Bar strategies don't act on ticks."""
        return StrategyDecision()

    def __init__(
        self,
        symbol: str = "QQQ",
        sma_period: int = 9,
        mode: Literal["directional", "straddle"] = "directional",
        contracts: int = 1,
        profit_target_pct: Decimal = Decimal("30"),
        stop_loss_pct: Decimal = Decimal("25"),
        time_stop_minutes_before_close: int = 30,
        entry_delay_minutes_after_open: int = 10,
        session_open: time = time(13, 30, tzinfo=UTC),
        session_close: time = time(20, 0, tzinfo=UTC),
    ) -> None:
        if sma_period <= 0:
            raise ValueError("sma_period must be positive")
        if contracts < 1:
            raise ValueError("contracts must be >= 1")
        if mode not in ("directional", "straddle"):
            raise ValueError(f"unknown mode: {mode!r}")
        if session_close.tzinfo is None:
            raise ValueError("session_close must be timezone-aware")
        if session_open.tzinfo is None:
            raise ValueError("session_open must be timezone-aware")
        if entry_delay_minutes_after_open < 0:
            raise ValueError("entry_delay_minutes_after_open must be >= 0")

        self.symbol = symbol
        self.sma_period = sma_period
        self.mode = mode
        self.contracts = contracts
        self.profit_target_pct = Decimal(profit_target_pct)
        self.stop_loss_pct = Decimal(stop_loss_pct)
        self.time_stop_minutes_before_close = time_stop_minutes_before_close
        self.entry_delay_minutes_after_open = entry_delay_minutes_after_open
        self.session_open = session_open
        self.session_close = session_close

        self._bars: list[Bar] = []
        self._prev_diff: Decimal | None = None
        self._open_legs: dict[tuple[str, str, str, str], _OpenLeg] = {}

    def reset_session(self) -> None:
        """Drop intraday state at the start of a new trading session.

        Session VWAP and the SMA/VWAP cross detector depend on intraday
        bars only -- when replaying multi-day data (Supabase-bars backtest
        or the live engine across midnight) the caller must invoke this
        on each session boundary, otherwise prior-day bars contaminate
        VWAP and crosses stop firing. Open positions in _open_legs are
        intentionally preserved; the caller decides whether to flatten
        them across sessions.
        """
        self._bars.clear()
        self._prev_diff = None

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _contract_key(c: OptionContract) -> tuple[str, str, str, str]:
        return (c.underlying, c.expiry.isoformat(), str(c.strike), c.right)

    def _session_close_dt(self, now: datetime) -> datetime:
        """Combine ``now``'s date with the configured session-close time."""

        return datetime.combine(now.date(), self.session_close)

    def _within_time_stop(self, now: datetime) -> bool:
        close_dt = self._session_close_dt(now)
        cutoff = close_dt - timedelta(minutes=self.time_stop_minutes_before_close)
        return now >= cutoff

    def _session_open_dt(self, now: datetime) -> datetime:
        return datetime.combine(now.date(), self.session_open)

    def _in_trade_window(self, now: datetime) -> bool:
        """True iff `now` is between (open + delay) and (close - time_stop).

        Used to gate signal *emission* — VWAP/SMA/cross state still update
        outside the window so plotted data stays continuous.
        """
        open_dt = self._session_open_dt(now)
        entry_open = open_dt + timedelta(minutes=self.entry_delay_minutes_after_open)
        if now < entry_open:
            return False
        if self._within_time_stop(now):
            return False
        return True

    def _pick_atm_quote(
        self,
        quotes: list[OptionQuote],
        underlying_close: Decimal,
        right: Literal["C", "P"],
    ) -> OptionQuote | None:
        candidates = [q for q in quotes if q.right == right and q.underlying == self.symbol]
        if not candidates:
            return None
        return min(candidates, key=lambda q: abs(q.strike - underlying_close))

    def _make_entry_intent(
        self,
        quote: OptionQuote,
        now: datetime,
        direction: SignalDirection,
    ) -> OrderIntent:
        contract = quote.contract()
        return OrderIntent(
            intent_id=uuid.uuid4(),
            created_at=now,
            symbol=self.symbol,
            is_option=True,
            option=contract,
            side=OrderSide.BUY,
            quantity=self.contracts,
            order_type=OrderType.LIMIT,
            limit_price=quote.mid,
            tag=f"entry:{direction.value}",
        )

    def _make_exit_intent(
        self,
        leg: _OpenLeg,
        current_mid: Decimal,
        now: datetime,
        reason: str,
    ) -> OrderIntent:
        return OrderIntent(
            intent_id=uuid.uuid4(),
            created_at=now,
            symbol=self.symbol,
            is_option=True,
            option=leg.contract,
            side=OrderSide.SELL,
            quantity=leg.quantity,
            order_type=OrderType.LIMIT,
            limit_price=current_mid,
            tag=f"exit:{reason}",
        )

    def _register_leg(
        self,
        intent: OrderIntent,
        entry_mid: Decimal,
        entry_time: datetime,
    ) -> None:
        assert intent.option is not None
        leg = _OpenLeg(
            contract=intent.option,
            quantity=intent.quantity,
            entry_mid=entry_mid,
            entry_intent_id=intent.intent_id,
            entry_time=entry_time,
        )
        self._open_legs[self._contract_key(intent.option)] = leg

    # ------------------------------------------------------------------ on_bar

    def on_bar(self, ctx: StrategyContext) -> StrategyDecision:
        if ctx.last_bar is None:
            return StrategyDecision()

        bar = ctx.last_bar
        # Only buffer bars for our configured symbol — keep the strategy
        # robust if upstream multiplexes feeds.
        if bar.symbol != self.symbol:
            return StrategyDecision()

        self._bars.append(bar)

        sma = _sma([b.close for b in self._bars], self.sma_period)
        if sma is None:
            return StrategyDecision()

        vwap = _bar_vwap(bar, self._bars)
        if vwap is None:
            return StrategyDecision()

        diff = sma - vwap
        prev_diff = self._prev_diff
        self._prev_diff = diff

        if prev_diff is None:
            return StrategyDecision()

        cross_up = prev_diff < 0 <= diff
        cross_down = prev_diff > 0 >= diff
        if not (cross_up or cross_down):
            return StrategyDecision()

        # Gate signal emission to the configured trade window: open + 10 min
        # through close - 30 min by default. Bars/SMA/VWAP keep updating
        # outside this band; only the signal record is suppressed.
        if not self._in_trade_window(ctx.now):
            return StrategyDecision()

        # Don't double-stack — strategy-level guard in addition to the
        # orchestrator's max_open_positions check.
        if ctx.open_positions >= 1 or self._open_legs:
            return StrategyDecision()

        direction = SignalDirection.LONG_VOL_UP if cross_up else SignalDirection.LONG_VOL_DOWN
        signal = Signal(
            name=self.name,
            direction=direction,
            timestamp=ctx.now,
            symbol=self.symbol,
            metadata={
                "scope": "portfolio",
                "sma": str(sma),
                "vwap": str(vwap),
                "close": str(bar.close),
                "mode": self.mode,
            },
        )

        intents: list[OrderIntent] = []
        if self.mode == "directional":
            right: Literal["C", "P"] = "C" if cross_up else "P"
            atm = self._pick_atm_quote(ctx.option_quotes, bar.close, right)
            if atm is None:
                # No tradable contract pre-staged — emit signal only.
                return StrategyDecision(signals=[signal])
            intent = self._make_entry_intent(atm, ctx.now, direction)
            intents.append(intent)
            self._register_leg(intent, atm.mid, ctx.now)
        else:  # straddle
            call = self._pick_atm_quote(ctx.option_quotes, bar.close, "C")
            put = self._pick_atm_quote(ctx.option_quotes, bar.close, "P")
            if call is None or put is None:
                return StrategyDecision(signals=[signal])
            for q in (call, put):
                intent = self._make_entry_intent(q, ctx.now, direction)
                intents.append(intent)
                self._register_leg(intent, q.mid, ctx.now)

        return StrategyDecision(signals=[signal], intents=intents)

    # ----------------------------------------------------------- on_option_quote

    def on_option_quote(self, ctx: StrategyContext) -> StrategyDecision:
        if not self._open_legs:
            return StrategyDecision()

        # Index incoming quotes by contract identity for O(1) lookup.
        quote_index: dict[tuple[str, str, str, str], OptionQuote] = {}
        for q in ctx.option_quotes:
            quote_index[self._contract_key(q.contract())] = q

        time_stop_now = self._within_time_stop(ctx.now)

        signals: list[Signal] = []
        intents: list[OrderIntent] = []
        closed_keys: list[tuple[str, str, str, str]] = []

        # Iterate over a stable snapshot so we can mutate _open_legs after.
        for key, leg in self._open_legs.items():
            quote = quote_index.get(key)
            current_mid = quote.mid if quote is not None else None

            reason: str | None = None
            exit_price: Decimal | None = None

            if current_mid is not None and leg.entry_mid > 0:
                pnl_pct = (current_mid - leg.entry_mid) / leg.entry_mid * Decimal(100)
                if pnl_pct >= self.profit_target_pct:
                    reason = "profit"
                    exit_price = current_mid
                elif pnl_pct <= -self.stop_loss_pct:
                    reason = "stop"
                    exit_price = current_mid

            if reason is None and time_stop_now:
                reason = "time"
                # Use last seen mid if available, else fall back to entry mid.
                exit_price = current_mid if current_mid is not None else leg.entry_mid

            if reason is None or exit_price is None:
                continue

            signals.append(
                Signal(
                    name=self.name,
                    direction=SignalDirection.EXIT,
                    timestamp=ctx.now,
                    symbol=self.symbol,
                    metadata={
                        "scope": "portfolio",
                        "reason": reason,
                        "entry_mid": str(leg.entry_mid),
                        "exit_mid": str(exit_price),
                        "right": leg.contract.right,
                        "strike": str(leg.contract.strike),
                    },
                )
            )
            intents.append(self._make_exit_intent(leg, exit_price, ctx.now, reason))
            closed_keys.append(key)

        for key in closed_keys:
            self._open_legs.pop(key, None)

        return StrategyDecision(signals=signals, intents=intents)


__all__ = ["BuyVolQQQCrossStrategy"]
