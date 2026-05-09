"""Synthetic options feed — Black-Scholes priced quotes around an equity feed."""

from __future__ import annotations

import math
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, time
from decimal import Decimal

from contracts.data_feed import (
    Bar,
    ChainSnapshot,
    MarketDataFeed,
    OptionContract,
    OptionQuote,
    OptionRight,
    Quote,
)

from engine.data_feeds.base import BaseFeed

# 4pm ET = 20:00 UTC during DST (close enough for v1 — the contract treats
# expiry resolution as best-effort; no DST gymnastics here).
_EXPIRY_UTC_HOUR = 20
_SECONDS_PER_YEAR = 365 * 86400
_MIN_T_SECONDS = 60
_INV_SQRT_2 = 1.0 / math.sqrt(2.0)
_INV_SQRT_2PI = 1.0 / math.sqrt(2.0 * math.pi)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x * _INV_SQRT_2))


def _norm_pdf(x: float) -> float:
    return _INV_SQRT_2PI * math.exp(-0.5 * x * x)


def _bs_d1_d2(s: float, k: float, t: float, r: float, sigma: float) -> tuple[float, float]:
    if s <= 0 or k <= 0 or t <= 0 or sigma <= 0:
        raise ValueError("Black-Scholes inputs must be strictly positive")
    d1 = (math.log(s / k) + (r + 0.5 * sigma * sigma) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    return d1, d2


def _bs_price(
    s: float, k: float, t: float, r: float, sigma: float, right: OptionRight
) -> float:
    d1, d2 = _bs_d1_d2(s, k, t, r, sigma)
    if right == "C":
        return s * _norm_cdf(d1) - k * math.exp(-r * t) * _norm_cdf(d2)
    return k * math.exp(-r * t) * _norm_cdf(-d2) - s * _norm_cdf(-d1)


def _bs_greeks(
    s: float, k: float, t: float, r: float, sigma: float, right: OptionRight
) -> tuple[float, float, float, float]:
    """Return (delta, gamma, theta_per_day, vega_per_1pct)."""
    d1, d2 = _bs_d1_d2(s, k, t, r, sigma)
    pdf_d1 = _norm_pdf(d1)
    sqrt_t = math.sqrt(t)
    gamma = pdf_d1 / (s * sigma * sqrt_t)
    vega = s * pdf_d1 * sqrt_t  # per 1.00 change in sigma
    if right == "C":
        delta = _norm_cdf(d1)
        theta = (
            -(s * pdf_d1 * sigma) / (2 * sqrt_t)
            - r * k * math.exp(-r * t) * _norm_cdf(d2)
        )
    else:
        delta = _norm_cdf(d1) - 1.0
        theta = (
            -(s * pdf_d1 * sigma) / (2 * sqrt_t)
            + r * k * math.exp(-r * t) * _norm_cdf(-d2)
        )
    return delta, gamma, theta / 365.0, vega / 100.0


def _to_decimal(value: float) -> Decimal:
    return Decimal(str(round(value, 6)))


class SyntheticOptionsFeed(BaseFeed):
    """Wrap an equity feed and synthesize Black-Scholes option quotes.

    Equity streaming methods delegate to the wrapped feed. ``get_option_chain``
    generates ATM ±5 strikes (rounded to nearest 1.0 — appropriate for QQQ)
    around the latest equity bar close. ``stream_option_quotes`` yields one
    ``OptionQuote`` per requested contract using the latest underlying close
    and the configured implied vol.
    """

    name: str = "synthetic_options"

    def __init__(
        self,
        equity_feed: MarketDataFeed,
        iv: Decimal = Decimal("0.20"),
        risk_free_rate: Decimal = Decimal("0.05"),
    ) -> None:
        if not isinstance(iv, Decimal):
            raise TypeError("iv must be Decimal")
        if not isinstance(risk_free_rate, Decimal):
            raise TypeError("risk_free_rate must be Decimal")
        if iv <= 0:
            raise ValueError("iv must be > 0")
        self._equity = equity_feed
        self._iv = iv
        self._r = risk_free_rate
        self._last_close: dict[str, Decimal] = {}

    # -- helpers -------------------------------------------------------------

    def _record_close(self, symbol: str, close: Decimal) -> None:
        self._last_close[symbol.upper()] = close

    async def _latest_close(self, symbol: str) -> Decimal:
        sym = symbol.upper()
        if sym in self._last_close:
            return self._last_close[sym]
        last: Decimal | None = None
        async for bar in self._equity.stream_equity_bars(sym, 60):
            last = bar.close
        if last is None:
            raise RuntimeError(
                f"unable to determine latest close for {sym}: equity feed yielded no bars"
            )
        self._last_close[sym] = last
        return last

    @staticmethod
    def _expiry_datetime(expiry: date) -> datetime:
        return datetime.combine(
            expiry, time(hour=_EXPIRY_UTC_HOUR, tzinfo=UTC)
        )

    @classmethod
    def _time_to_expiry_years(cls, expiry: date, now: datetime | None = None) -> float:
        ref = now or datetime.now(tz=UTC)
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=UTC)
        seconds = (cls._expiry_datetime(expiry) - ref).total_seconds()
        seconds = max(seconds, _MIN_T_SECONDS)
        return seconds / _SECONDS_PER_YEAR

    # -- equity passthrough --------------------------------------------------

    async def stream_equity_bars(
        self, symbol: str, interval_seconds: int = 60
    ) -> AsyncIterator[Bar]:
        sym = self._validate_symbol(symbol)
        async for bar in self._equity.stream_equity_bars(sym, interval_seconds):
            self._record_close(bar.symbol, bar.close)
            yield bar

    async def stream_equity_quotes(self, symbol: str) -> AsyncIterator[Quote]:
        sym = self._validate_symbol(symbol)
        async for quote in self._equity.stream_equity_quotes(sym):
            if quote.last is not None:
                self._record_close(quote.symbol, quote.last)
            yield quote

    # -- option chain --------------------------------------------------------

    async def get_option_chain(self, underlying: str, expiry: date) -> ChainSnapshot:
        sym = self._validate_symbol(underlying)
        close = await self._latest_close(sym)
        atm = int(close.to_integral_value(rounding="ROUND_HALF_UP"))
        contracts: list[OptionContract] = []
        for offset in range(-5, 6):
            strike = Decimal(atm + offset)
            for right in ("C", "P"):
                contracts.append(
                    OptionContract(
                        underlying=sym,
                        expiry=expiry,
                        strike=strike,
                        right=right,  # type: ignore[arg-type]
                    )
                )
        return ChainSnapshot(
            underlying=sym,
            expiry=expiry,
            snapshot_time=datetime.now(tz=UTC),
            contracts=contracts,
        )

    async def stream_option_quotes(
        self, contracts: list[OptionContract]
    ) -> AsyncIterator[OptionQuote]:
        if not contracts:
            return
        now = datetime.now(tz=UTC)
        sigma = float(self._iv)
        r = float(self._r)
        for contract in contracts:
            close = await self._latest_close(contract.underlying)
            s = float(close)
            k = float(contract.strike)
            t = self._time_to_expiry_years(contract.expiry, now=now)
            price = _bs_price(s, k, t, r, sigma, contract.right)
            delta, gamma, theta, vega = _bs_greeks(s, k, t, r, sigma, contract.right)
            mid = max(price, 0.0)
            half_spread = max(0.01, mid * 0.02)
            bid = max(0.0, mid - half_spread)
            ask = mid + half_spread
            yield OptionQuote(
                underlying=contract.underlying,
                expiry=contract.expiry,
                strike=contract.strike,
                right=contract.right,
                timestamp=now,
                bid=_to_decimal(bid),
                ask=_to_decimal(ask),
                last=_to_decimal(mid),
                iv=self._iv,
                delta=_to_decimal(delta),
                gamma=_to_decimal(gamma),
                theta=_to_decimal(theta),
                vega=_to_decimal(vega),
            )
