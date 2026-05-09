"""Tests for BuyVolQQQCrossTickStrategy."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from contracts.broker import OrderSide
from contracts.data_feed import OptionQuote, Quote
from contracts.strategy import SignalDirection, StrategyContext
from engine.strategies.buy_vol_qqq_cross_tick import BuyVolQQQCrossTickStrategy

# ──────────────────────────────────────────────────────────── helpers ──


def _quote(ts: datetime, mid: Decimal, last: Decimal | None = None,
           volume: int = 0) -> Quote:
    bid = mid - Decimal("0.01")
    ask = mid + Decimal("0.01")
    return Quote(
        symbol="QQQ", timestamp=ts, bid=bid, ask=ask,
        last=last if last is not None else mid, volume=volume,
    )


def _atm_oqs(expiry: date, center_strike: Decimal,
             mid: Decimal = Decimal("1.05")) -> list[OptionQuote]:
    """Build a 5-wide synthetic chain centered on `center_strike` so the
    strategy can find an ATM quote regardless of small price movements."""
    ts = datetime(2026, 4, 15, 14, 0, tzinfo=UTC)
    quotes: list[OptionQuote] = []
    for offset in (-2, -1, 0, 1, 2):
        strike = center_strike + Decimal(offset)
        for right in ("C", "P"):
            quotes.append(OptionQuote(
                underlying="QQQ", expiry=expiry, strike=strike,
                right=right, timestamp=ts,  # type: ignore[arg-type]
                bid=mid - Decimal("0.05"),
                ask=mid + Decimal("0.05"),
            ))
    return quotes


def _ts(seconds: float) -> datetime:
    return datetime(2026, 4, 15, 14, 0, tzinfo=UTC) + \
        timedelta(seconds=seconds)


class _Tape:
    """Stateful test driver — tracks cumulative volume so VWAP math is correct
    across multiple drive() calls."""

    def __init__(self, strategy, oqs: list[OptionQuote] | None = None) -> None:
        self.strategy = strategy
        self.cum_volume = 0
        self.oqs = oqs if oqs is not None else _atm_oqs(date(2026, 4, 15), Decimal("450"))

    def push(self, ts: datetime, mid: Decimal, vol_increment: int = 100,
             open_positions: int = 0):
        self.cum_volume += vol_increment
        tick = _quote(ts, mid, last=mid, volume=self.cum_volume)
        ctx = StrategyContext(
            now=ts, last_tick=tick, option_quotes=self.oqs,
            open_positions=open_positions, cash_available=Decimal("5000"),
        )
        return self.strategy.on_tick(ctx)

    def drive(self, samples, vol_per_step: int = 100, open_positions: int = 0):
        last = None
        for ts, mid in samples:
            last = self.push(ts, mid, vol_increment=vol_per_step,
                             open_positions=open_positions)
        return last

    def prime_vwap(self, anchor_price: Decimal, anchor_volume: int = 1_000_000):
        # Two ticks: first sets _last_volume baseline, second pumps anchor volume.
        self.push(_ts(-2), anchor_price, vol_increment=0)
        self.push(_ts(-1), anchor_price, vol_increment=anchor_volume)


def _prime_below(strat) -> _Tape:
    """Anchor VWAP at 450 then drive SMA below it (sign=-1).

    Returns the _Tape so callers can keep pushing without losing volume state.
    """
    tape = _Tape(strat)
    tape.prime_vwap(Decimal("450.00"))
    tape.drive([(_ts(i), Decimal("449.00")) for i in range(3)])
    assert strat._last_diff_sign == -1, \
        f"priming should establish negative sign; got {strat._last_diff_sign}"
    return tape


# ───────────────────────────────────────────────────────────── tests ──


def test_no_signal_until_window_filled():
    strat = BuyVolQQQCrossTickStrategy(sma_window_seconds=5, confirmation_seconds=2)
    tape = _Tape(strat)
    decision = tape.drive([(_ts(i), Decimal("450.00")) for i in range(4)])
    assert decision is not None
    assert decision.signals == []
    assert decision.intents == []


def test_cross_up_signal_then_pending_then_entry_after_confirmation():
    strat = BuyVolQQQCrossTickStrategy(sma_window_seconds=3, confirmation_seconds=2)
    tape = _prime_below(strat)

    tape.drive([(_ts(3), Decimal("451.00")),
                (_ts(4), Decimal("451.00")),
                (_ts(5), Decimal("451.00"))])
    assert strat._pending is not None
    assert strat._pending[0] == SignalDirection.LONG_VOL_UP
    assert strat._open_legs == {}

    tape.drive([(_ts(6), Decimal("451.00")), (_ts(7), Decimal("451.00"))])
    assert strat._pending is None
    assert len(strat._open_legs) == 1


def test_pending_entry_cancelled_on_reverse_within_window():
    """If the cross reverses within the confirmation window, the original
    pending entry must be cancelled WITHOUT firing an entry. A fresh
    pending in the opposite direction is allowed (correct per spec — user
    is OK with re-cross trades) but it must not have fired yet either."""
    strat = BuyVolQQQCrossTickStrategy(sma_window_seconds=3, confirmation_seconds=5)
    tape = _prime_below(strat)

    tape.drive([(_ts(i), Decimal("451.00")) for i in range(3, 6)])
    assert strat._pending is not None
    assert strat._pending[0] == SignalDirection.LONG_VOL_UP
    queued_at_up = strat._pending[1]

    tape.drive([(_ts(6), Decimal("449.00")), (_ts(7), Decimal("449.00"))])
    # The UP pending was cancelled — either pending is None, or it's a
    # newly-armed DOWN pending (not the same UP one we saw above).
    if strat._pending is not None:
        assert strat._pending[0] == SignalDirection.LONG_VOL_DOWN
        assert strat._pending[1] != queued_at_up
    # Critically: no entry intent fired during the abort
    assert strat._open_legs == {}


def test_straddle_mode_emits_two_intents_on_confirmed_cross():
    strat = BuyVolQQQCrossTickStrategy(
        sma_window_seconds=3, confirmation_seconds=1, mode="straddle",
    )
    tape = _prime_below(strat)

    all_buys: list = []
    for i in range(3, 8):
        decision = tape.push(_ts(i), Decimal("451.00"))
        all_buys.extend([x for x in decision.intents if x.side == OrderSide.BUY])

    assert len(all_buys) == 2, f"expected 2 BUY intents (call+put); got {len(all_buys)}"
    rights = sorted(i.option.right for i in all_buys)  # type: ignore[union-attr]
    assert rights == ["C", "P"]


def test_open_position_blocks_new_entry():
    strat = BuyVolQQQCrossTickStrategy(sma_window_seconds=3, confirmation_seconds=1)
    tape = _prime_below(strat)
    tape.drive([(_ts(i), Decimal("451.00")) for i in range(3, 6)])
    tape.drive([(_ts(6), Decimal("451.00")), (_ts(7), Decimal("451.00"))])
    assert len(strat._open_legs) == 1
    pre_legs = dict(strat._open_legs)

    # Subsequent ticks with open_positions=1 should NOT add a new leg
    tape.drive([(_ts(i), Decimal("452.00")) for i in range(8, 14)],
               open_positions=1)
    assert strat._open_legs == pre_legs


def test_profit_target_triggers_exit():
    strat = BuyVolQQQCrossTickStrategy(sma_window_seconds=3, confirmation_seconds=1)
    tape = _prime_below(strat)
    tape.drive([(_ts(i), Decimal("451.00")) for i in range(3, 6)])
    tape.drive([(_ts(6), Decimal("451.00")), (_ts(7), Decimal("451.00"))])
    assert len(strat._open_legs) == 1

    key = next(iter(strat._open_legs))
    expiry, strike, right = key
    leg = strat._open_legs[key]
    high_oqs = [
        OptionQuote(
            underlying="QQQ", expiry=expiry, strike=strike, right=right,  # type: ignore[arg-type]
            timestamp=_ts(8),
            bid=leg.entry_mid + Decimal("0.40"),
            ask=leg.entry_mid + Decimal("0.50"),
        )
    ]
    decision = strat.on_option_quote(StrategyContext(
        now=_ts(8), option_quotes=high_oqs, cash_available=Decimal("5000"),
    ))
    assert any(i.tag == "exit:profit" and i.side == OrderSide.SELL for i in decision.intents)
    assert strat._open_legs == {}


def test_stop_loss_triggers_exit():
    strat = BuyVolQQQCrossTickStrategy(sma_window_seconds=3, confirmation_seconds=1)
    tape = _prime_below(strat)
    tape.drive([(_ts(i), Decimal("451.00")) for i in range(3, 6)])
    tape.drive([(_ts(6), Decimal("451.00")), (_ts(7), Decimal("451.00"))])
    assert len(strat._open_legs) == 1
    key = next(iter(strat._open_legs))
    expiry, strike, right = key
    leg = strat._open_legs[key]

    low_oqs = [
        OptionQuote(
            underlying="QQQ", expiry=expiry, strike=strike, right=right,  # type: ignore[arg-type]
            timestamp=_ts(8),
            bid=leg.entry_mid - Decimal("0.40"),
            ask=leg.entry_mid - Decimal("0.30"),
        )
    ]
    decision = strat.on_option_quote(StrategyContext(
        now=_ts(8), option_quotes=low_oqs, cash_available=Decimal("5000"),
    ))
    assert any(i.tag == "exit:stop" for i in decision.intents)
    assert strat._open_legs == {}


def test_invalid_window_or_confirmation_raises():
    with pytest.raises(ValueError):
        BuyVolQQQCrossTickStrategy(sma_window_seconds=0)
    with pytest.raises(ValueError):
        BuyVolQQQCrossTickStrategy(confirmation_seconds=-1)
    with pytest.raises(ValueError):
        BuyVolQQQCrossTickStrategy(mode="weird")  # type: ignore[arg-type]


def test_session_reset_clears_window_and_vwap():
    strat = BuyVolQQQCrossTickStrategy(sma_window_seconds=3, confirmation_seconds=1)
    tape = _Tape(strat)
    tape.drive([(_ts(i), Decimal("450.00")) for i in range(3)])

    next_day = datetime(2026, 4, 16, 14, 0, tzinfo=UTC)
    tape.push(next_day, Decimal("451.00"), vol_increment=100)
    assert len(strat._sec_samples) <= 1
    assert strat._last_diff_sign == 0


def test_on_bar_is_noop():
    strat = BuyVolQQQCrossTickStrategy()
    decision = strat.on_bar(StrategyContext(
        now=_ts(0), cash_available=Decimal("5000"),
    ))
    assert decision.signals == []
    assert decision.intents == []
    assert strat.kind == "tick"
