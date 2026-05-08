"""Tick-driven SMA(N-sec)/session-VWAP cross long-vol strategy.

Differences from BuyVolQQQCrossStrategy (bar version):

1. **Input**: every NBBO tick (Quote), not 1-minute bar closes.
2. **SMA**: mean of last N 1-second mid-price snapshots (default N=9). The
   strategy snaps each second's last seen mid into a fixed-size deque, so
   "9-second SMA on tick data" rather than "SMA of 9 ticks".
3. **VWAP**: cumulative session VWAP from trade prints. Each tick that
   carries a fresh `last` price + an increase in cumulative `volume` adds
   `(last * delta_volume)` to the running numerator.
4. **Confirmation gate**: cross detection arms a pending entry. The entry
   only fires when the SMA-vs-VWAP differential has held the same sign for
   `confirmation_seconds` (default 5s) of monotonic wall time. If the
   differential flips during the window, the pending entry is discarded;
   no trade.
5. **Re-cross after entry**: a flip while a position is open does NOT
   create a new opposite entry directly — exits are still driven by
   profit/stop/time. After the position closes, a fresh pending entry can
   be armed by a future cross.
6. **Exits unchanged**: profit_target_pct / stop_loss_pct / time_stop work
   exactly like the bar strategy on `on_option_quote`.

The strategy is deterministic: every clock read flows through ctx.now,
random uuids flow through uuid.uuid4 (callers monkeypatch in tests).
"""

from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import Literal

from contracts.broker import OrderIntent, OrderSide, OrderType
from contracts.data_feed import OptionContract, OptionQuote
from contracts.strategy import (
    Signal,
    SignalDirection,
    StrategyContext,
    StrategyDecision,
)

_DEFAULT_OPEN = time(13, 30, tzinfo=UTC)   # 9:30am ET in UTC (DST)
_DEFAULT_CLOSE = time(20, 0, tzinfo=UTC)   # 4pm ET in UTC (DST)


@dataclass
class _OpenLeg:
    contract: OptionContract
    entry_mid: Decimal
    entry_time: datetime
    side: OrderSide  # always BUY for long-vol entries


class BuyVolQQQCrossTickStrategy:
    """Tick-driven long-vol strategy with 5-sec entry confirmation."""

    name: str = "buy_vol_qqq_cross_tick"
    kind: str = "tick"

    def __init__(
        self,
        symbol: str = "QQQ",
        sma_window_seconds: int = 9,
        confirmation_seconds: int = 5,
        mode: Literal["directional", "straddle"] = "directional",
        contracts: int = 1,
        profit_target_pct: Decimal = Decimal("30"),
        stop_loss_pct: Decimal = Decimal("25"),
        time_stop_minutes_before_close: int = 30,
        entry_delay_minutes_after_open: int = 10,
        session_open: time = _DEFAULT_OPEN,
        session_close: time = _DEFAULT_CLOSE,
    ) -> None:
        if sma_window_seconds <= 0:
            raise ValueError("sma_window_seconds must be positive")
        if confirmation_seconds < 0:
            raise ValueError("confirmation_seconds must be >= 0")
        if entry_delay_minutes_after_open < 0:
            raise ValueError("entry_delay_minutes_after_open must be >= 0")
        if mode not in ("directional", "straddle"):
            raise ValueError(f"unknown mode: {mode!r}")

        self.symbol = symbol
        self.sma_window_seconds = sma_window_seconds
        self.confirmation_seconds = confirmation_seconds
        self.mode = mode
        self.contracts = contracts
        self.profit_target_pct = Decimal(profit_target_pct)
        self.stop_loss_pct = Decimal(stop_loss_pct)
        self.time_stop_minutes_before_close = time_stop_minutes_before_close
        self.entry_delay_minutes_after_open = entry_delay_minutes_after_open
        self.session_open = session_open
        self.session_close = session_close

        # Per-second mid samples: maps second-truncated-ts -> last seen mid
        self._sec_samples: deque[tuple[datetime, Decimal]] = deque(
            maxlen=sma_window_seconds
        )
        self._cur_sec: datetime | None = None
        self._cur_sec_mid: Decimal | None = None

        # Session VWAP state
        self._vwap_pv: Decimal = Decimal("0")
        self._vwap_v: Decimal = Decimal("0")
        self._last_volume: Decimal | None = None
        self._session_date: object | None = None  # ctx.now.date() of first tick

        # Cross state
        self._last_diff_sign: int = 0  # -1 / 0 / +1

        # Pending entry confirmation: (direction, queued_at, last_seen_at)
        self._pending: tuple[SignalDirection, datetime] | None = None

        # Held-position registry, keyed by (expiry, strike, right)
        self._open_legs: dict[tuple[object, Decimal, str], _OpenLeg] = {}

    # ──────────────────────────────────────────────────────── public ────

    def on_bar(self, ctx: StrategyContext) -> StrategyDecision:
        """Tick strategies ignore bar callbacks."""
        return StrategyDecision()

    def on_tick(self, ctx: StrategyContext) -> StrategyDecision:
        if ctx.last_tick is None:
            return StrategyDecision()
        tick = ctx.last_tick
        if tick.symbol != self.symbol:
            return StrategyDecision()

        # ─── reset session state at first tick of a new trading day ──
        tick_date = tick.timestamp.date()
        if self._session_date is None or tick_date != self._session_date:
            self._reset_session(tick_date)

        # ─── update VWAP from incremental volume * last trade price ───
        if tick.last is not None and tick.volume is not None:
            cur_v = Decimal(tick.volume)
            if self._last_volume is None:
                self._last_volume = cur_v
            delta_v = cur_v - self._last_volume
            if delta_v > 0:
                self._vwap_pv += Decimal(tick.last) * delta_v
                self._vwap_v += delta_v
            self._last_volume = cur_v

        # ─── 1-sec snap of mid-price ──────────────────────────────────
        sec_ts = tick.timestamp.replace(microsecond=0)
        mid = tick.mid
        if self._cur_sec is None or sec_ts != self._cur_sec:
            # Closing the previous second: record its last-seen mid into
            # the rolling window, then start a new second.
            if self._cur_sec is not None and self._cur_sec_mid is not None:
                self._sec_samples.append((self._cur_sec, self._cur_sec_mid))
            self._cur_sec = sec_ts
            self._cur_sec_mid = mid
        else:
            # Mid-second update: keep the latest mid for this second
            self._cur_sec_mid = mid

        # ─── compute SMA, VWAP, cross ─────────────────────────────────
        sma = self._sma()
        vwap = self._vwap()
        signals: list[Signal] = []
        intents: list[OrderIntent] = []

        # ─── exits: drive on every tick that updates a held option ───
        intents.extend(self._exit_intents(ctx))

        if sma is None or vwap is None:
            return StrategyDecision(signals=signals, intents=intents)

        diff = sma - vwap
        new_sign = 1 if diff > 0 else (-1 if diff < 0 else 0)

        # Cross detection — but only EMIT signals + arm pending entries
        # inside the configured trade window. State (_last_diff_sign etc.)
        # still tracks so charting/audit data remains continuous.
        in_window = self._in_trade_window(ctx.now)
        if (
            in_window
            and self._last_diff_sign != 0
            and new_sign not in (0, self._last_diff_sign)
        ):
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
            self._pending = (direction, ctx.now)

        # ─── pending-entry maintenance ────────────────────────────────
        if self._pending is not None:
            pending_dir, queued_at = self._pending
            # If diff sign reversed against the pending direction → cancel
            pending_sign = 1 if pending_dir == SignalDirection.LONG_VOL_UP else -1
            if new_sign not in (0, pending_sign):
                self._pending = None
            else:
                elapsed = (ctx.now - queued_at).total_seconds()
                if elapsed >= self.confirmation_seconds:
                    if not self._gating_blocks_entry(ctx):
                        intents.extend(self._build_entries(ctx, pending_dir))
                    self._pending = None

        if new_sign != 0:
            self._last_diff_sign = new_sign

        return StrategyDecision(signals=signals, intents=intents)

    def on_option_quote(self, ctx: StrategyContext) -> StrategyDecision:
        """Drive exits when held option quotes update."""
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
        self._pending = None
        # NOTE: open_legs deliberately NOT cleared across sessions; positions
        # held overnight (rare for 0DTE but possible) keep their entry data.

    def _sma(self) -> Decimal | None:
        # Include the in-progress current second for responsiveness
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

    def _gating_blocks_entry(self, ctx: StrategyContext) -> bool:
        if ctx.open_positions >= 1 or self._open_legs:
            return True
        if not self._in_trade_window(ctx.now):
            return True
        return False

    def _cutoff_time(self, now: datetime) -> datetime:
        close_dt = datetime.combine(
            now.date(), self.session_close, tzinfo=now.tzinfo or UTC
        )
        return close_dt - timedelta(minutes=self.time_stop_minutes_before_close)

    def _entry_open_time(self, now: datetime) -> datetime:
        open_dt = datetime.combine(
            now.date(), self.session_open, tzinfo=now.tzinfo or UTC
        )
        return open_dt + timedelta(minutes=self.entry_delay_minutes_after_open)

    def _in_trade_window(self, now: datetime) -> bool:
        """True iff `now` is between (open + delay) and (close - time_stop)."""
        if now < self._entry_open_time(now):
            return False
        if now >= self._cutoff_time(now):
            return False
        return True

    def _build_entries(
        self, ctx: StrategyContext, direction: SignalDirection
    ) -> list[OrderIntent]:
        """Build BUY OrderIntent(s) for the pending direction."""
        if direction == SignalDirection.LONG_VOL_UP:
            rights: tuple[str, ...] = ("C",) if self.mode == "directional" else ("C", "P")
        elif direction == SignalDirection.LONG_VOL_DOWN:
            rights = ("P",) if self.mode == "directional" else ("C", "P")
        else:
            return []

        last_tick = ctx.last_tick
        if last_tick is None:
            return []
        atm_strike = self._round_strike(last_tick.mid)

        intents: list[OrderIntent] = []
        for right in rights:
            quote = self._pick_atm_quote(ctx.option_quotes, atm_strike, right)
            if quote is None:
                continue
            contract = OptionContract(
                underlying=self.symbol,
                expiry=quote.expiry,
                strike=quote.strike,
                right=right,  # type: ignore[arg-type]
            )
            tag = (
                "entry:LONG_VOL_UP"
                if direction == SignalDirection.LONG_VOL_UP
                else "entry:LONG_VOL_DOWN"
            )
            intent = OrderIntent(
                intent_id=uuid.uuid4(),
                created_at=ctx.now,
                symbol=self.symbol,
                is_option=True,
                option=contract,
                side=OrderSide.BUY,
                quantity=self.contracts,
                order_type=OrderType.LIMIT,
                limit_price=quote.mid,
                tag=tag,
            )
            intents.append(intent)
            self._open_legs[(contract.expiry, contract.strike, right)] = _OpenLeg(
                contract=contract,
                entry_mid=quote.mid,
                entry_time=ctx.now,
                side=OrderSide.BUY,
            )
        return intents

    def _exit_intents(self, ctx: StrategyContext) -> list[OrderIntent]:
        if not self._open_legs:
            return []
        intents: list[OrderIntent] = []
        cutoff = self._cutoff_time(ctx.now)
        for key, leg in list(self._open_legs.items()):
            quote = self._pick_atm_quote(ctx.option_quotes, leg.contract.strike, leg.contract.right)
            mid = quote.mid if quote is not None else None

            reason: str | None = None
            if mid is not None and leg.entry_mid > 0:
                pnl_pct = (mid - leg.entry_mid) / leg.entry_mid * Decimal("100")
                if pnl_pct >= self.profit_target_pct:
                    reason = "exit:profit"
                elif pnl_pct <= -self.stop_loss_pct:
                    reason = "exit:stop"
            if reason is None and ctx.now >= cutoff:
                reason = "exit:time"

            if reason is None:
                continue

            exit_price = mid if mid is not None else leg.entry_mid
            intent = OrderIntent(
                intent_id=uuid.uuid4(),
                created_at=ctx.now,
                symbol=self.symbol,
                is_option=True,
                option=leg.contract,
                side=OrderSide.SELL,
                quantity=self.contracts,
                order_type=OrderType.LIMIT,
                limit_price=exit_price,
                tag=reason,
            )
            intents.append(intent)
            del self._open_legs[key]
        return intents

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
        # QQQ trades in $1 strikes; round half-up to integer.
        return Decimal(int(price + Decimal("0.5")))
