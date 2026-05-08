"""Tests for SellPutQQQCrossStrategy.

Covers:
  * Cross-down arms a SELL-to-open put intent at the ATM strike.
  * Two cross-down signals 25s apart -> only the first arms an entry; the
    second is suppressed by the 30s cooldown.
  * Held short put with mid declining through 0.75x / 0.50x / 0.00x entry
    -> exactly three exit BUYs fire, each for 25 percent of original qty,
    leaving 25 percent open.
  * Held short put with mid spiking to 2.0x entry -> single exit BUY for
    the full remaining quantity with tag ``exit:stop_200pct``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from contracts.broker import OrderSide
from contracts.data_feed import OptionQuote, Quote
from contracts.strategy import StrategyContext
from engine.strategies.sell_put_qqq_cross import (
    SellPutQQQCrossStrategy,
    TakeProfitTier,
    default_tiers,
)

# ──────────────────────────────────────────────────────── helpers ──

def _q(ts: datetime, mid: Decimal, *, last: Decimal | None = None,
       volume: int = 0) -> Quote:
    bid = mid - Decimal("0.01")
    ask = mid + Decimal("0.01")
    return Quote(
        symbol="QQQ", timestamp=ts, bid=bid, ask=ask,
        last=last if last is not None else mid, volume=volume,
    )


def _atm_oqs(
    expiry: date,
    center_strike: Decimal,
    *,
    put_mid: Decimal = Decimal("1.00"),
    ts: datetime | None = None,
) -> list[OptionQuote]:
    """5-strike chain at +/-2 around center, both calls and puts."""
    when = ts or datetime(2026, 4, 15, 14, 0, tzinfo=UTC)
    out: list[OptionQuote] = []
    for offset in (-2, -1, 0, 1, 2):
        strike = center_strike + Decimal(offset)
        for right in ("C", "P"):
            out.append(OptionQuote(
                underlying="QQQ", expiry=expiry, strike=strike,
                right=right, timestamp=when,  # type: ignore[arg-type]
                bid=put_mid - Decimal("0.05"),
                ask=put_mid + Decimal("0.05"),
            ))
    return out


def _ts(seconds: float) -> datetime:
    return datetime(2026, 4, 15, 14, 0, tzinfo=UTC) + timedelta(seconds=seconds)


class _Tape:
    """Stateful test driver — tracks cumulative volume + per-leg option quotes."""

    def __init__(
        self,
        strategy: SellPutQQQCrossStrategy,
        oqs: list[OptionQuote] | None = None,
    ) -> None:
        self.strategy = strategy
        self.cum_volume = 0
        self.oqs = oqs if oqs is not None else _atm_oqs(
            date(2026, 4, 15), Decimal("450"),
        )

    def push(self, ts: datetime, mid: Decimal, *, vol_increment: int = 100,
             open_positions: int = 0):
        self.cum_volume += vol_increment
        tick = _q(ts, mid, last=mid, volume=self.cum_volume)
        ctx = StrategyContext(
            now=ts, last_tick=tick, option_quotes=self.oqs,
            open_positions=open_positions, cash_available=Decimal("5000"),
        )
        return self.strategy.on_tick(ctx)

    def drive(self, samples, *, vol_per_step: int = 100, open_positions: int = 0):
        last = None
        for ts, mid in samples:
            last = self.push(ts, mid, vol_increment=vol_per_step,
                             open_positions=open_positions)
        return last

    def push_option_quote(self, ts: datetime, put_mid: Decimal, *,
                          open_positions: int = 1):
        """Drive the on_option_quote path with a fresh put-mid for the held strike."""
        oqs = _atm_oqs(date(2026, 4, 15), Decimal("450"),
                       put_mid=put_mid, ts=ts)
        ctx = StrategyContext(
            now=ts, last_tick=None, option_quotes=oqs,
            open_positions=open_positions, cash_available=Decimal("5000"),
        )
        return self.strategy.on_option_quote(ctx)

    def prime_above(self) -> None:
        """Anchor VWAP at 450 then drive SMA above it (sign=+1)."""
        self.push(_ts(-2), Decimal("450.00"), vol_increment=0)
        self.push(_ts(-1), Decimal("450.00"), vol_increment=1_000_000)
        for i in range(3):
            self.push(_ts(i), Decimal("451.00"))
        assert self.strategy._last_diff_sign == 1


# ───────────────────────────────────────────────────────── tests ──

def test_cross_down_arms_sell_to_open_put():
    strat = SellPutQQQCrossStrategy(sma_window_seconds=3, contracts=4)
    tape = _Tape(strat)
    tape.prime_above()

    # Now drive SMA below VWAP — should sign-flip to -1 and emit a SELL put intent
    decisions = []
    for i in range(3, 8):
        d = tape.push(_ts(i), Decimal("449.00"))
        decisions.append(d)

    sell_intents = [
        intent
        for d in decisions
        for intent in d.intents
        if intent.side == OrderSide.SELL
    ]
    assert len(sell_intents) == 1
    intent = sell_intents[0]
    assert intent.is_option is True
    assert intent.option is not None
    assert intent.option.right == "P"
    assert intent.quantity == 4
    assert intent.tag == "entry:SELL_PUT"
    assert len(strat._open_legs) == 1


def test_cooldown_suppresses_second_signal_within_30s():
    strat = SellPutQQQCrossStrategy(sma_window_seconds=3, contracts=4,
                                    cooldown_seconds=30)
    tape = _Tape(strat)
    tape.prime_above()

    # First cross-down at t=3 → fires
    tape.drive([(_ts(i), Decimal("449.00")) for i in range(3, 6)])
    assert strat._last_signal_at is not None
    first_at = strat._last_signal_at
    assert len(strat._open_legs) == 1

    # Cross back up at t=10 (would arm a new signal but cooldown blocks)
    tape.drive([(_ts(i), Decimal("451.00")) for i in range(10, 14)])
    # Still inside the 30s window after first_at — the second signal must be suppressed
    assert strat._last_signal_at == first_at, \
        "cooldown should have prevented the cross-up signal from updating _last_signal_at"

    # After the 30s window passes, a new signal CAN fire
    after_cd_ts = first_at + timedelta(seconds=31)
    # Need a proper cross to re-arm — drive back through SMA
    samples = [(after_cd_ts + timedelta(seconds=k), Decimal("449.00"))
               for k in range(0, 4)]
    tape.drive(samples)
    assert strat._last_signal_at is not None
    assert strat._last_signal_at > first_at


def test_tier_ladder_closes_25_pct_at_each_threshold():
    strat = SellPutQQQCrossStrategy(sma_window_seconds=3, contracts=4)
    tape = _Tape(strat)
    tape.prime_above()
    tape.drive([(_ts(i), Decimal("449.00")) for i in range(3, 6)])
    assert len(strat._open_legs) == 1
    leg = next(iter(strat._open_legs.values()))
    entry_mid = leg.entry_mid
    # entry_mid = chain put_mid (1.00) by construction

    # Tier 1: option drops 25% → close 25% (1 contract)
    d = tape.push_option_quote(_ts(20), put_mid=entry_mid * Decimal("0.74"))
    tier1 = [i for i in d.intents if i.side == OrderSide.BUY]
    assert len(tier1) == 1
    assert tier1[0].quantity == 1
    assert tier1[0].tag == "exit:tier_25pct"

    # Tier 2: option drops 50% → close another 25% (1 contract)
    d = tape.push_option_quote(_ts(30), put_mid=entry_mid * Decimal("0.49"))
    tier2 = [i for i in d.intents if i.side == OrderSide.BUY]
    assert len(tier2) == 1
    assert tier2[0].quantity == 1
    assert tier2[0].tag == "exit:tier_50pct"

    # Tier 3: option drops 100% (worthless) → close another 25% (1 contract)
    d = tape.push_option_quote(_ts(40), put_mid=Decimal("0.00"))
    tier3 = [i for i in d.intents if i.side == OrderSide.BUY]
    assert len(tier3) == 1
    assert tier3[0].quantity == 1
    assert tier3[0].tag == "exit:tier_100pct"

    # 25% remains open (1 of 4 contracts)
    remaining_legs = [
        leg for leg in strat._open_legs.values()
        if leg.entry_qty - leg.closed_qty_so_far > 0
    ]
    assert len(remaining_legs) == 1
    assert remaining_legs[0].entry_qty - remaining_legs[0].closed_qty_so_far == 1


def test_stop_loss_fires_full_close_at_2x_entry():
    strat = SellPutQQQCrossStrategy(sma_window_seconds=3, contracts=4,
                                    stop_loss_multiple=Decimal("2.0"))
    tape = _Tape(strat)
    tape.prime_above()
    tape.drive([(_ts(i), Decimal("449.00")) for i in range(3, 6)])
    assert len(strat._open_legs) == 1
    leg = next(iter(strat._open_legs.values()))
    entry_mid = leg.entry_mid

    # Mid spikes to 2.05x entry - should close ALL 4 contracts in one intent
    d = tape.push_option_quote(_ts(50), put_mid=entry_mid * Decimal("2.05"))
    stop_intents = [i for i in d.intents if i.side == OrderSide.BUY]
    assert len(stop_intents) == 1
    assert stop_intents[0].quantity == 4
    assert stop_intents[0].tag == "exit:stop_200pct"
    # Leg should be removed
    assert strat._open_legs == {}


def test_default_tiers_match_user_spec():
    tiers = default_tiers()
    assert len(tiers) == 3
    assert tiers[0].gain_pct == Decimal("25") and tiers[0].qty_fraction == Decimal("0.25")
    assert tiers[1].gain_pct == Decimal("50") and tiers[1].qty_fraction == Decimal("0.25")
    assert tiers[2].gain_pct == Decimal("100") and tiers[2].qty_fraction == Decimal("0.25")
    # Sum = 0.75 → 25 % runs to expiry, matching user spec
    assert sum(t.qty_fraction for t in tiers) == Decimal("0.75")


def test_invalid_constructor_args_rejected():
    with pytest.raises(ValueError, match=">= 4"):
        SellPutQQQCrossStrategy(contracts=3)
    with pytest.raises(ValueError, match=">= 0"):
        SellPutQQQCrossStrategy(cooldown_seconds=-1)
    with pytest.raises(ValueError, match="> 1"):
        SellPutQQQCrossStrategy(stop_loss_multiple=Decimal("0.9"))
    with pytest.raises(ValueError, match="qty_fraction"):
        SellPutQQQCrossStrategy(
            take_profit_tiers=[TakeProfitTier(gain_pct=Decimal("25"),
                                              qty_fraction=Decimal("1.5"))],
        )
