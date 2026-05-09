"""Short-put SMA9/VWAP cross strategy with cooldown + tiered scale-out.

Inspired by `MAKaminski/alpha-gen-trading` (alpha-gen v1) but explicitly
tailored to alpha-kite-v2's contract shape and adds a tiered take-profit
ladder that the v1 system did not have.

Behavior summary
----------------

1. Drives off NBBO ticks (``kind = "tick"``).
2. Maintains a 9-second SMA of mid-price snapshots and a session VWAP from
   incremental trade volume — same logic as
   :class:`engine.strategies.buy_vol_qqq_cross_tick.BuyVolQQQCrossTickStrategy`.
3. On a cross-down (SMA below VWAP) → sell ATM put-to-open (``side=SELL``).
   IBKR opens a short-put position from a SELL on a contract not currently
   held, so this works through the existing :class:`OrderIntent` shape.
4. On a cross-up (SMA above VWAP) → no entry. We are scoped to short puts
   only; the alpha-gen-style call-side leg is intentionally omitted.
5. Cooldown: any signal (up or down) arms a wall-clock timer. New signals
   inside ``cooldown_seconds`` (default 30) are dropped — both the Signal
   record and the entry attempt — to match the alpha-gen rule.
6. Trade window: emission and entry-arming gated to
   ``[session_open + entry_delay_after_open, session_close - time_stop_before_close]``
   like the long-vol tick strategy.

Exits
-----

We track ``entry_qty`` and ``closed_qty_so_far`` per leg so the tier ladder
knows how much of the original size remains. On every option-quote update:

* ``mid <= entry_mid * (1 - tier.gain_pct/100)`` → close ``tier.qty_fraction``
  of ``entry_qty`` with ``tag = "exit:tier_<gain>pct"``.
* ``mid >= entry_mid * stop_loss_multiple`` → close all remaining qty with
  ``tag = "exit:stop_<mult*100>pct"``.
* At ``close - time_stop_minutes_before_close`` → sweep remaining qty with
  ``tag = "exit:time"``.

The default ladder = the user's spec: 25/50/100 percent gains close 25 %
each; the final 25 % runs.
"""

from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

from contracts.broker import OrderIntent, OrderSide, OrderType
from contracts.data_feed import OptionContract, OptionQuote
from contracts.strategy import (
    Signal,
    SignalDirection,
    StrategyContext,
    StrategyDecision,
)

_DEFAULT_OPEN = time(13, 30, tzinfo=UTC)   # 9:30am ET DST
_DEFAULT_CLOSE = time(20, 0, tzinfo=UTC)   # 4pm ET DST


@dataclass(frozen=True)
class TakeProfitTier:
    """One step of the scale-out ladder."""

    gain_pct: Decimal     # close when mid has dropped this many percent
    qty_fraction: Decimal # fraction of original entry_qty to close at this tier


def default_tiers() -> list[TakeProfitTier]:
    """User spec: 25/50/100 % gains, 25 % qty each, 25 % runs."""
    return [
        TakeProfitTier(gain_pct=Decimal("25"), qty_fraction=Decimal("0.25")),
        TakeProfitTier(gain_pct=Decimal("50"), qty_fraction=Decimal("0.25")),
        TakeProfitTier(gain_pct=Decimal("100"), qty_fraction=Decimal("0.25")),
    ]


@dataclass
class _OpenLeg:
    contract: OptionContract
    entry_mid: Decimal
    entry_time: datetime
    entry_qty: int
    closed_qty_so_far: int = 0
    tiers_hit: set[int] = field(default_factory=set)   # indices of tiers already executed


class SellPutQQQCrossStrategy:
    """Short-put cross strategy with cooldown + tiered take-profit ladder."""

    name: str = "sell_put_qqq_cross"
    kind: str = "tick"

    def __init__(
        self,
        symbol: str = "QQQ",
        sma_window_seconds: int = 9,
        cooldown_seconds: int = 30,
        contracts: int = 4,
        stop_loss_multiple: Decimal = Decimal("2.0"),
        take_profit_tiers: list[TakeProfitTier] | None = None,
        time_stop_minutes_before_close: int = 30,
        entry_delay_minutes_after_open: int = 10,
        session_open: time = _DEFAULT_OPEN,
        session_close: time = _DEFAULT_CLOSE,
    ) -> None:
        if sma_window_seconds <= 0:
            raise ValueError("sma_window_seconds must be positive")
        if cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be >= 0")
        if contracts < 4:
            # Tier ladder closes 25% per tier; with <4 contracts we can't
            # actually close a quarter without rounding to zero.
            raise ValueError("contracts must be >= 4 to support 25% tier closes")
        if entry_delay_minutes_after_open < 0:
            raise ValueError("entry_delay_minutes_after_open must be >= 0")
        if stop_loss_multiple <= 1:
            raise ValueError("stop_loss_multiple must be > 1 (loss when mid > entry)")
        tiers = list(take_profit_tiers) if take_profit_tiers is not None else default_tiers()
        if any(t.qty_fraction <= 0 or t.qty_fraction > 1 for t in tiers):
            raise ValueError("each tier qty_fraction must be in (0, 1]")
        if sum(t.qty_fraction for t in tiers) > Decimal("1"):
            raise ValueError("tier qty_fractions must sum to <= 1.0")

        self.symbol = symbol
        self.sma_window_seconds = sma_window_seconds
        self.cooldown_seconds = cooldown_seconds
        self.contracts = contracts
        self.stop_loss_multiple = Decimal(stop_loss_multiple)
        self.tiers = tiers
        self.time_stop_minutes_before_close = time_stop_minutes_before_close
        self.entry_delay_minutes_after_open = entry_delay_minutes_after_open
        self.session_open = session_open
        self.session_close = session_close

        # Per-second mid samples for SMA
        self._sec_samples: deque[tuple[datetime, Decimal]] = deque(
            maxlen=sma_window_seconds
        )
        self._cur_sec: datetime | None = None
        self._cur_sec_mid: Decimal | None = None

        # Session VWAP state
        self._vwap_pv: Decimal = Decimal("0")
        self._vwap_v: Decimal = Decimal("0")
        self._last_volume: Decimal | None = None
        self._session_date: object | None = None

        # Cross + cooldown state
        self._last_diff_sign: int = 0
        self._last_signal_at: datetime | None = None

        # Held-position registry, keyed by (expiry, strike, right)
        self._open_legs: dict[tuple[object, Decimal, str], _OpenLeg] = {}

    # ──────────────────────────────────────────────────────── public ────

    def on_bar(self, ctx: StrategyContext) -> StrategyDecision:
        return StrategyDecision()

    def on_tick(self, ctx: StrategyContext) -> StrategyDecision:
        if ctx.last_tick is None:
            return StrategyDecision()
        tick = ctx.last_tick
        if tick.symbol != self.symbol:
            return StrategyDecision()

        tick_date = tick.timestamp.date()
        if self._session_date is None or tick_date != self._session_date:
            self._reset_session(tick_date)

        # VWAP from incremental trade volume
        if tick.last is not None and tick.volume is not None:
            cur_v = Decimal(tick.volume)
            if self._last_volume is None:
                self._last_volume = cur_v
            delta_v = cur_v - self._last_volume
            if delta_v > 0:
                self._vwap_pv += Decimal(tick.last) * delta_v
                self._vwap_v += delta_v
            self._last_volume = cur_v

        # 1-sec mid snap
        sec_ts = tick.timestamp.replace(microsecond=0)
        mid = tick.mid
        if self._cur_sec is None or sec_ts != self._cur_sec:
            if self._cur_sec is not None and self._cur_sec_mid is not None:
                self._sec_samples.append((self._cur_sec, self._cur_sec_mid))
            self._cur_sec = sec_ts
            self._cur_sec_mid = mid
        else:
            self._cur_sec_mid = mid

        sma = self._sma()
        vwap = self._vwap()
        signals: list[Signal] = []
        intents: list[OrderIntent] = []

        # Exits run unconditionally (they don't care about trade window)
        intents.extend(self._exit_intents(ctx))

        if sma is None or vwap is None:
            return StrategyDecision(signals=signals, intents=intents)

        diff = sma - vwap
        new_sign = 1 if diff > 0 else (-1 if diff < 0 else 0)

        in_window = self._in_trade_window(ctx.now)
        cross_detected = (
            self._last_diff_sign != 0
            and new_sign not in (0, self._last_diff_sign)
        )
        cooldown_active = (
            self._last_signal_at is not None
            and (ctx.now - self._last_signal_at).total_seconds() < self.cooldown_seconds
        )

        if in_window and cross_detected and not cooldown_active:
            direction = (
                SignalDirection.LONG_VOL_UP
                if new_sign > 0
                else SignalDirection.LONG_VOL_DOWN
            )
            signals.append(
                Signal(
                    name=self.name,
                    direction=direction,
                    timestamp=ctx.now,
                    symbol=self.symbol,
                    metadata={"sma": str(sma), "vwap": str(vwap)},
                )
            )
            self._last_signal_at = ctx.now

            # Only the cross-DOWN direction arms an entry — we sell puts when
            # the SMA dips below VWAP. Cross-up still arms the cooldown but
            # produces no order intent (single-direction strategy).
            if (
                new_sign < 0
                and ctx.open_positions == 0
                and not self._open_legs
            ):
                intents.extend(self._build_entries(ctx))

        if new_sign != 0:
            self._last_diff_sign = new_sign

        return StrategyDecision(signals=signals, intents=intents)

    def on_option_quote(self, ctx: StrategyContext) -> StrategyDecision:
        return StrategyDecision(signals=[], intents=self._exit_intents(ctx))

    # ──────────────────────────────────────────────────────── private ───

    def _reset_session(self, tick_date) -> None:  # type: ignore[no-untyped-def]
        self._sec_samples.clear()
        self._cur_sec = None
        self._cur_sec_mid = None
        self._vwap_pv = Decimal("0")
        self._vwap_v = Decimal("0")
        self._last_volume = None
        self._session_date = tick_date
        self._last_diff_sign = 0
        self._last_signal_at = None

    def _sma(self) -> Decimal | None:
        samples = list(self._sec_samples)
        if self._cur_sec is not None and self._cur_sec_mid is not None:
            samples.append((self._cur_sec, self._cur_sec_mid))
        if len(samples) < self.sma_window_seconds:
            return None
        recent = samples[-self.sma_window_seconds :]
        total = sum((s[1] for s in recent), Decimal("0"))
        return total / Decimal(self.sma_window_seconds)

    def _vwap(self) -> Decimal | None:
        if self._vwap_v <= 0:
            return None
        return self._vwap_pv / self._vwap_v

    def _entry_open_time(self, now: datetime) -> datetime:
        open_dt = datetime.combine(
            now.date(), self.session_open, tzinfo=now.tzinfo or UTC
        )
        return open_dt + timedelta(minutes=self.entry_delay_minutes_after_open)

    def _cutoff_time(self, now: datetime) -> datetime:
        close_dt = datetime.combine(
            now.date(), self.session_close, tzinfo=now.tzinfo or UTC
        )
        return close_dt - timedelta(minutes=self.time_stop_minutes_before_close)

    def _in_trade_window(self, now: datetime) -> bool:
        if now < self._entry_open_time(now):
            return False
        if now >= self._cutoff_time(now):
            return False
        return True

    def _build_entries(self, ctx: StrategyContext) -> list[OrderIntent]:
        last_tick = ctx.last_tick
        if last_tick is None:
            return []
        atm_strike = self._round_strike(last_tick.mid)
        quote = self._pick_atm_quote(ctx.option_quotes, atm_strike, "P")
        if quote is None:
            return []

        contract = OptionContract(
            underlying=self.symbol,
            expiry=quote.expiry,
            strike=quote.strike,
            right="P",
        )
        intent = OrderIntent(
            intent_id=uuid.uuid4(),
            created_at=ctx.now,
            symbol=self.symbol,
            is_option=True,
            option=contract,
            side=OrderSide.SELL,           # SELL on a not-held option = SELL_TO_OPEN
            quantity=self.contracts,
            order_type=OrderType.LIMIT,
            limit_price=quote.mid,
            tag="entry:SELL_PUT",
        )
        self._open_legs[(contract.expiry, contract.strike, "P")] = _OpenLeg(
            contract=contract,
            entry_mid=quote.mid,
            entry_time=ctx.now,
            entry_qty=self.contracts,
        )
        return [intent]

    def _exit_intents(self, ctx: StrategyContext) -> list[OrderIntent]:
        if not self._open_legs:
            return []
        intents: list[OrderIntent] = []
        cutoff = self._cutoff_time(ctx.now)

        for key, leg in list(self._open_legs.items()):
            quote = self._pick_atm_quote(
                ctx.option_quotes, leg.contract.strike, leg.contract.right,
            )
            mid = quote.mid if quote is not None else None

            remaining = leg.entry_qty - leg.closed_qty_so_far
            if remaining <= 0:
                del self._open_legs[key]
                continue

            # 1) Stop-loss — full close. Highest priority.
            if mid is not None and mid >= leg.entry_mid * self.stop_loss_multiple:
                intents.append(self._exit_intent(
                    leg, qty=remaining, price=mid,
                    tag=f"exit:stop_{int(self.stop_loss_multiple * 100)}pct",
                    now=ctx.now,
                ))
                leg.closed_qty_so_far = leg.entry_qty
                del self._open_legs[key]
                continue

            # 2) Tier ladder — partial closes for each newly-crossed tier.
            #    A tier hits when mid drops to entry * (1 - gain_pct/100).
            if mid is not None and leg.entry_mid > 0:
                for idx, tier in enumerate(self.tiers):
                    if idx in leg.tiers_hit:
                        continue
                    threshold = leg.entry_mid * (
                        Decimal("1") - tier.gain_pct / Decimal("100")
                    )
                    if mid <= threshold:
                        tier_qty = int(leg.entry_qty * tier.qty_fraction)
                        # Don't close more than what's left.
                        tier_qty = min(tier_qty, leg.entry_qty - leg.closed_qty_so_far)
                        if tier_qty <= 0:
                            leg.tiers_hit.add(idx)
                            continue
                        intents.append(self._exit_intent(
                            leg, qty=tier_qty, price=mid,
                            tag=f"exit:tier_{int(tier.gain_pct)}pct",
                            now=ctx.now,
                        ))
                        leg.closed_qty_so_far += tier_qty
                        leg.tiers_hit.add(idx)

            # 3) End-of-session sweep — close whatever runs hasn't already
            #    closed itself out.
            still_remaining = leg.entry_qty - leg.closed_qty_so_far
            if still_remaining > 0 and ctx.now >= cutoff:
                exit_price = mid if mid is not None else leg.entry_mid
                intents.append(self._exit_intent(
                    leg, qty=still_remaining, price=exit_price,
                    tag="exit:time", now=ctx.now,
                ))
                leg.closed_qty_so_far = leg.entry_qty
                del self._open_legs[key]
                continue

            # If the leg is fully closed by tiers, drop it.
            if leg.closed_qty_so_far >= leg.entry_qty:
                del self._open_legs[key]

        return intents

    def _exit_intent(
        self,
        leg: _OpenLeg,
        *,
        qty: int,
        price: Decimal,
        tag: str,
        now: datetime,
    ) -> OrderIntent:
        # BUY-to-close on a short-option position: side=BUY, same contract.
        return OrderIntent(
            intent_id=uuid.uuid4(),
            created_at=now,
            symbol=self.symbol,
            is_option=True,
            option=leg.contract,
            side=OrderSide.BUY,
            quantity=qty,
            order_type=OrderType.LIMIT,
            limit_price=price,
            tag=tag,
        )

    @staticmethod
    def _pick_atm_quote(
        quotes: list[OptionQuote], strike: Decimal, right: str
    ) -> OptionQuote | None:
        for q in quotes:
            if q.strike == strike and q.right == right:
                return q
        return None

    @staticmethod
    def _round_strike(price: Decimal) -> Decimal:
        return Decimal(int(price + Decimal("0.5")))


__all__ = [
    "SellPutQQQCrossStrategy",
    "TakeProfitTier",
    "default_tiers",
]
