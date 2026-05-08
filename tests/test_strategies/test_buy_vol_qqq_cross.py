"""Unit tests for ``engine.strategies.buy_vol_qqq_cross``.

These tests do not touch the broker or feed: they construct StrategyContext
objects directly and replay them through the strategy. Every value is a
``Decimal`` and every clock read is supplied via ``ctx.now``.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from contracts.broker import OrderSide, OrderType
from contracts.data_feed import Bar, OptionQuote
from contracts.strategy import SignalDirection, StrategyContext, StrategyDecision
from engine.strategies.buy_vol_qqq_cross import BuyVolQQQCrossStrategy

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "qqq_2026-04-15_1min.json"

# Pre-computed (see scratch script): with sma_period=9 and the bar.vwap field,
# the first cross-up is at bar index 19 (open_time 2026-04-15T13:49:00Z) and
# the first cross-down is at index 47 (open_time 2026-04-15T14:17:00Z).
EXPECTED_FIRST_CROSS_UP_INDEX = 19
EXPECTED_FIRST_CROSS_UP_TIME = datetime(2026, 4, 15, 13, 49, tzinfo=UTC)
EXPECTED_FIRST_CROSS_DOWN_INDEX = 47


# ---------------------------------------------------------------- fixtures


def _load_bars() -> list[Bar]:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    bars: list[Bar] = []
    for b in raw["bars"]:
        bars.append(
            Bar(
                symbol=b["symbol"],
                interval_seconds=int(b["interval_seconds"]),
                open_time=datetime.fromisoformat(b["open_time"]),
                open=Decimal(b["open"]),
                high=Decimal(b["high"]),
                low=Decimal(b["low"]),
                close=Decimal(b["close"]),
                volume=int(b["volume"]),
                vwap=Decimal(b["vwap"]) if b.get("vwap") is not None else None,
            )
        )
    return bars


def _atm_quotes(
    underlying: str,
    expiry: date,
    underlying_close: Decimal,
    ts: datetime,
    *,
    call_bid: Decimal = Decimal("1.00"),
    call_ask: Decimal = Decimal("1.10"),
    put_bid: Decimal = Decimal("1.00"),
    put_ask: Decimal = Decimal("1.10"),
) -> list[OptionQuote]:
    """Build a 3-strike chain centred on the integer-rounded underlying close."""

    center = Decimal(int(underlying_close.quantize(Decimal("1"))))
    quotes: list[OptionQuote] = []
    for offset in (Decimal("-1"), Decimal("0"), Decimal("1")):
        strike = center + offset
        quotes.append(
            OptionQuote(
                underlying=underlying,
                expiry=expiry,
                strike=strike,
                right="C",
                timestamp=ts,
                bid=call_bid,
                ask=call_ask,
            )
        )
        quotes.append(
            OptionQuote(
                underlying=underlying,
                expiry=expiry,
                strike=strike,
                right="P",
                timestamp=ts,
                bid=put_bid,
                ask=put_ask,
            )
        )
    return quotes


def _replay(
    strategy: BuyVolQQQCrossStrategy,
    bars: list[Bar],
    *,
    quotes_for_index: dict[int, list[OptionQuote]] | None = None,
    open_positions: int = 0,
) -> list[tuple[int, StrategyDecision]]:
    """Replay bars through ``on_bar`` and collect non-empty decisions."""

    out: list[tuple[int, StrategyDecision]] = []
    for i, bar in enumerate(bars):
        quotes: list[OptionQuote] = []
        if quotes_for_index and i in quotes_for_index:
            quotes = quotes_for_index[i]
        ctx = StrategyContext(
            now=bar.open_time + timedelta(seconds=bar.interval_seconds),
            last_bar=bar,
            bar_history=list(bars[: i + 1]),
            option_quotes=quotes,
            open_positions=open_positions,
            cash_available=Decimal("100000"),
        )
        decision = strategy.on_bar(ctx)
        if decision.signals or decision.intents:
            out.append((i, decision))
    return out


# ------------------------------------------------------------------ tests


def test_cross_up_emits_long_vol_up_signal_at_expected_index() -> None:
    bars = _load_bars()
    strategy = BuyVolQQQCrossStrategy()

    cross_idx = EXPECTED_FIRST_CROSS_UP_INDEX
    quotes_for_index = {
        cross_idx: _atm_quotes(
            underlying="QQQ",
            expiry=date(2026, 4, 15),
            underlying_close=bars[cross_idx].close,
            ts=bars[cross_idx].open_time,
        ),
    }

    decisions = _replay(strategy, bars, quotes_for_index=quotes_for_index)

    assert len(decisions) == 1, f"expected exactly one decision, got {len(decisions)}"
    idx, decision = decisions[0]
    assert idx == cross_idx
    assert len(decision.signals) == 1
    sig = decision.signals[0]
    assert sig.direction == SignalDirection.LONG_VOL_UP
    assert sig.symbol == "QQQ"
    assert sig.timestamp == EXPECTED_FIRST_CROSS_UP_TIME + timedelta(seconds=60)

    assert len(decision.intents) == 1
    intent = decision.intents[0]
    assert intent.is_option is True
    assert intent.option is not None
    assert intent.option.right == "C"
    assert intent.side == OrderSide.BUY
    assert intent.order_type == OrderType.LIMIT
    assert intent.quantity == 1
    assert intent.tag == "entry:LONG_VOL_UP"
    # ATM strike: chain centred on rounded close (450).
    assert intent.option.strike == Decimal("450")
    # Limit price is mid of the chosen quote.
    assert intent.limit_price == Decimal("1.05")


def test_straddle_mode_emits_two_intents_on_cross() -> None:
    bars = _load_bars()
    strategy = BuyVolQQQCrossStrategy(mode="straddle")

    cross_idx = EXPECTED_FIRST_CROSS_UP_INDEX
    quotes_for_index = {
        cross_idx: _atm_quotes(
            underlying="QQQ",
            expiry=date(2026, 4, 15),
            underlying_close=bars[cross_idx].close,
            ts=bars[cross_idx].open_time,
        ),
    }

    decisions = _replay(strategy, bars, quotes_for_index=quotes_for_index)

    assert len(decisions) == 1
    _, decision = decisions[0]
    assert len(decision.intents) == 2
    rights = sorted(i.option.right for i in decision.intents if i.option is not None)
    assert rights == ["C", "P"]
    assert all(i.side == OrderSide.BUY for i in decision.intents)
    assert all(i.tag == "entry:LONG_VOL_UP" for i in decision.intents)


def test_open_position_blocks_new_entries() -> None:
    bars = _load_bars()
    strategy = BuyVolQQQCrossStrategy()

    cross_idx = EXPECTED_FIRST_CROSS_UP_INDEX
    quotes_for_index = {
        cross_idx: _atm_quotes(
            underlying="QQQ",
            expiry=date(2026, 4, 15),
            underlying_close=bars[cross_idx].close,
            ts=bars[cross_idx].open_time,
        ),
    }

    decisions = _replay(
        strategy, bars, quotes_for_index=quotes_for_index, open_positions=1
    )

    # Strategy must not emit signals or intents when there's already an open
    # position upstream.
    assert decisions == []


def test_time_stop_blocks_entries_near_close() -> None:
    bars = _load_bars()
    # Use a session close shortly after our first cross so that the cross
    # falls inside the time-stop window.
    cross_bar_time = bars[EXPECTED_FIRST_CROSS_UP_INDEX].open_time
    session_close = (cross_bar_time + timedelta(minutes=5)).timetz()
    strategy = BuyVolQQQCrossStrategy(
        time_stop_minutes_before_close=30,
        session_close=session_close,
    )

    cross_idx = EXPECTED_FIRST_CROSS_UP_INDEX
    quotes_for_index = {
        cross_idx: _atm_quotes(
            underlying="QQQ",
            expiry=date(2026, 4, 15),
            underlying_close=bars[cross_idx].close,
            ts=bars[cross_idx].open_time,
        ),
    }

    decisions = _replay(strategy, bars, quotes_for_index=quotes_for_index)
    assert decisions == []


def test_profit_target_emits_exit() -> None:
    """A 30%+ unrealized gain must trigger an EXIT signal + SELL intent."""

    strategy = BuyVolQQQCrossStrategy(profit_target_pct=Decimal("30"))

    expiry = date(2026, 4, 15)
    underlying_close = Decimal("450.00")
    entry_ts = datetime(2026, 4, 15, 13, 50, tzinfo=UTC)

    # Drive an entry through on_bar by feeding a synthetic cross-up.
    # Build two bars: the first establishes prev_diff < 0; the second crosses up.
    pre_cross_bar = Bar(
        symbol="QQQ",
        interval_seconds=60,
        open_time=entry_ts - timedelta(minutes=1),
        open=underlying_close,
        high=underlying_close,
        low=underlying_close,
        close=underlying_close,
        volume=100,
        vwap=underlying_close + Decimal("1"),  # SMA < VWAP → diff < 0
    )
    cross_bar = Bar(
        symbol="QQQ",
        interval_seconds=60,
        open_time=entry_ts,
        open=underlying_close,
        high=underlying_close,
        low=underlying_close,
        close=underlying_close,
        volume=100,
        vwap=underlying_close - Decimal("1"),  # SMA > VWAP → diff > 0 (cross UP)
    )

    # Prime the SMA buffer with sma_period-1 closes equal to underlying_close
    # so the SMA is well-defined on the cross bar.
    primer_bars = [
        Bar(
            symbol="QQQ",
            interval_seconds=60,
            open_time=entry_ts - timedelta(minutes=10 - i),
            open=underlying_close,
            high=underlying_close,
            low=underlying_close,
            close=underlying_close,
            volume=100,
            vwap=underlying_close + Decimal("1"),
        )
        for i in range(8)  # 8 primer bars + pre_cross_bar = 9 (sma_period)
    ]

    # Replay primer + pre_cross with no quotes — strategy should not yet cross.
    for b in primer_bars + [pre_cross_bar]:
        ctx = StrategyContext(
            now=b.open_time + timedelta(seconds=60),
            last_bar=b,
            bar_history=[],
            option_quotes=[],
            open_positions=0,
            cash_available=Decimal("100000"),
        )
        decision = strategy.on_bar(ctx)
        assert not decision.intents

    # Now feed the cross bar with ATM quotes so an entry intent is emitted.
    entry_quotes = _atm_quotes(
        underlying="QQQ",
        expiry=expiry,
        underlying_close=underlying_close,
        ts=entry_ts,
        call_bid=Decimal("1.00"),
        call_ask=Decimal("1.10"),
        put_bid=Decimal("1.00"),
        put_ask=Decimal("1.10"),
    )
    ctx = StrategyContext(
        now=entry_ts + timedelta(seconds=60),
        last_bar=cross_bar,
        bar_history=[],
        option_quotes=entry_quotes,
        open_positions=0,
        cash_available=Decimal("100000"),
    )
    entry_decision = strategy.on_bar(ctx)
    assert len(entry_decision.intents) == 1
    entry_intent = entry_decision.intents[0]
    assert entry_intent.option is not None
    assert entry_intent.option.right == "C"
    assert entry_intent.limit_price == Decimal("1.05")

    # Now simulate a 50% mark-up on the held call, which is well over the 30% target.
    held = entry_intent.option
    profit_quote = OptionQuote(
        underlying=held.underlying,
        expiry=held.expiry,
        strike=held.strike,
        right=held.right,
        timestamp=entry_ts + timedelta(minutes=5),
        bid=Decimal("1.55"),
        ask=Decimal("1.60"),
    )
    exit_ctx = StrategyContext(
        now=entry_ts + timedelta(minutes=5),
        last_bar=None,
        bar_history=[],
        option_quotes=[profit_quote],
        open_positions=1,
        cash_available=Decimal("100000"),
    )
    exit_decision = strategy.on_option_quote(exit_ctx)

    assert len(exit_decision.signals) == 1
    assert exit_decision.signals[0].direction == SignalDirection.EXIT
    assert exit_decision.signals[0].metadata["reason"] == "profit"
    assert len(exit_decision.intents) == 1
    sell_intent = exit_decision.intents[0]
    assert sell_intent.side == OrderSide.SELL
    assert sell_intent.option == held
    assert sell_intent.tag == "exit:profit"
    assert sell_intent.limit_price == Decimal("1.575")  # mid of (1.55, 1.60)
    assert sell_intent.quantity == 1


def test_stop_loss_emits_exit() -> None:
    """A 25%+ unrealized loss must trigger an EXIT/stop signal + SELL intent."""

    strategy = BuyVolQQQCrossStrategy(stop_loss_pct=Decimal("25"))

    expiry = date(2026, 4, 15)
    underlying_close = Decimal("450.00")
    entry_ts = datetime(2026, 4, 15, 13, 50, tzinfo=UTC)

    # Same priming pattern as the profit-target test.
    primer_bars = [
        Bar(
            symbol="QQQ",
            interval_seconds=60,
            open_time=entry_ts - timedelta(minutes=10 - i),
            open=underlying_close,
            high=underlying_close,
            low=underlying_close,
            close=underlying_close,
            volume=100,
            vwap=underlying_close + Decimal("1"),
        )
        for i in range(8)
    ]
    pre_cross_bar = Bar(
        symbol="QQQ",
        interval_seconds=60,
        open_time=entry_ts - timedelta(minutes=1),
        open=underlying_close,
        high=underlying_close,
        low=underlying_close,
        close=underlying_close,
        volume=100,
        vwap=underlying_close + Decimal("1"),
    )
    cross_bar = Bar(
        symbol="QQQ",
        interval_seconds=60,
        open_time=entry_ts,
        open=underlying_close,
        high=underlying_close,
        low=underlying_close,
        close=underlying_close,
        volume=100,
        vwap=underlying_close - Decimal("1"),
    )

    for b in primer_bars + [pre_cross_bar]:
        strategy.on_bar(
            StrategyContext(
                now=b.open_time + timedelta(seconds=60),
                last_bar=b,
                bar_history=[],
                option_quotes=[],
                open_positions=0,
                cash_available=Decimal("100000"),
            )
        )

    entry_quotes = _atm_quotes(
        underlying="QQQ",
        expiry=expiry,
        underlying_close=underlying_close,
        ts=entry_ts,
        call_bid=Decimal("1.00"),
        call_ask=Decimal("1.10"),
        put_bid=Decimal("1.00"),
        put_ask=Decimal("1.10"),
    )
    entry_decision = strategy.on_bar(
        StrategyContext(
            now=entry_ts + timedelta(seconds=60),
            last_bar=cross_bar,
            bar_history=[],
            option_quotes=entry_quotes,
            open_positions=0,
            cash_available=Decimal("100000"),
        )
    )
    assert len(entry_decision.intents) == 1
    held = entry_decision.intents[0].option
    assert held is not None

    # 30% drawdown on entry mid 1.05 → mid 0.735 → bid/ask 0.71/0.76.
    loss_quote = OptionQuote(
        underlying=held.underlying,
        expiry=held.expiry,
        strike=held.strike,
        right=held.right,
        timestamp=entry_ts + timedelta(minutes=5),
        bid=Decimal("0.71"),
        ask=Decimal("0.76"),
    )
    exit_decision = strategy.on_option_quote(
        StrategyContext(
            now=entry_ts + timedelta(minutes=5),
            last_bar=None,
            bar_history=[],
            option_quotes=[loss_quote],
            open_positions=1,
            cash_available=Decimal("100000"),
        )
    )

    assert len(exit_decision.signals) == 1
    assert exit_decision.signals[0].direction == SignalDirection.EXIT
    assert exit_decision.signals[0].metadata["reason"] == "stop"
    assert len(exit_decision.intents) == 1
    sell_intent = exit_decision.intents[0]
    assert sell_intent.side == OrderSide.SELL
    assert sell_intent.tag == "exit:stop"
    assert sell_intent.option == held
    assert sell_intent.limit_price == Decimal("0.735")  # mid of (0.71, 0.76)
