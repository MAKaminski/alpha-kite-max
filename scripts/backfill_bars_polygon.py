"""Historical bar backfill via Polygon.io aggregates API.

Pulls bars (1m / 5m / 1h / 1d) for a symbol over a date range and writes
them into the same ``bars`` table the live engine uses. Use this to get
the multi-year 1-minute history that yfinance can't deliver (7-day cap)
and IBKR can't deliver via Railway (the gateway proxy issue we hit).

Requires:
  * ``POLYGON_API_KEY`` — paid Stocks Starter ($29/mo) or above gives
    you 5+ years of 1-min depth. Free tier works but is limited to
    2 years of EOD data only — fine for sanity-checking the script.
  * ``SUPABASE_DB_URL`` — same as the other backfill scripts.

Endpoint
--------

``GET /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to}``

Returns up to 50,000 bars per request, with a ``next_url`` for
pagination. 5 yrs x 252 days x 390 min ~= 491,400 bars at 1-min
resolution, so ~10 pages for the whole pull. Each page reads in
seconds — total wall time is ~1 minute for 5 years of 1-min, vs
~hours for IBKR.

Usage
-----

::

    SUPABASE_DB_URL=postgres://... \
    POLYGON_API_KEY=... \
        uv run python -m scripts.backfill_bars_polygon \
            --symbol QQQ --interval 60 --years 5

    # Or with explicit date range:
    uv run python -m scripts.backfill_bars_polygon \
        --symbol QQQ --interval 60 \
        --start 2021-01-01 --end 2026-05-12

    # All four resolutions in one shot:
    for i in 60 300 3600 86400; do
        uv run python -m scripts.backfill_bars_polygon --symbol QQQ --interval $i
    done

Idempotent — re-runs upsert into ``bars`` keyed on
``(symbol, interval_seconds, open_time)``, so duplicate windows just
overwrite.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from contracts.data_feed import Bar
from services.persistence.storage import SupabaseBackend
from services.persistence.writer import PersistenceWriter

LOG = logging.getLogger("alpha_kite.backfill_polygon")

_POLYGON_BASE = "https://api.polygon.io"
_PAGE_LIMIT = 50_000  # Polygon's max per request


@dataclass(frozen=True)
class _IntervalSpec:
    """Map our ``interval_seconds`` to Polygon's ``(multiplier, timespan)``."""

    seconds: int
    multiplier: int
    timespan: str  # minute / hour / day


_INTERVALS: dict[int, _IntervalSpec] = {
    60:    _IntervalSpec(60,    1,  "minute"),
    300:   _IntervalSpec(300,   5,  "minute"),
    3600:  _IntervalSpec(3600,  1,  "hour"),
    86400: _IntervalSpec(86400, 1,  "day"),
}


def _bar_from_polygon(symbol: str, interval_seconds: int, row: dict[str, Any]) -> Bar:
    """Polygon row shape:

    ``{"v": <volume>, "vw": <vwap>, "o": <open>, "c": <close>, "h": <high>,
       "l": <low>, "t": <ms-unix-epoch>, "n": <trade-count>}``
    """
    ts_ms = int(row["t"])
    open_time = datetime.fromtimestamp(ts_ms / 1000.0, tz=UTC)
    vwap = row.get("vw")
    return Bar(
        symbol=symbol,
        interval_seconds=interval_seconds,
        open_time=open_time,
        open=Decimal(str(row["o"])),
        high=Decimal(str(row["h"])),
        low=Decimal(str(row["l"])),
        close=Decimal(str(row["c"])),
        volume=int(row.get("v", 0) or 0),
        vwap=Decimal(str(vwap)) if vwap is not None else None,
    )


async def _fetch_page(
    httpx_client: Any, url: str, params: dict[str, Any] | None,
) -> dict[str, Any]:
    """One HTTP GET with retry on 429 (rate-limit) using Polygon's
    Retry-After header when present."""
    for attempt in range(5):
        resp = await httpx_client.get(url, params=params, timeout=30.0)
        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", "1.0"))
            LOG.warning("polygon 429; sleeping %.1fs (attempt %d)", retry_after, attempt + 1)
            await asyncio.sleep(retry_after)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError("polygon: exhausted retries on 429")


async def run(
    symbol: str,
    interval_seconds: int,
    start: datetime,
    end: datetime,
) -> dict[str, int]:
    if interval_seconds not in _INTERVALS:
        raise ValueError(
            f"interval_seconds must be one of {sorted(_INTERVALS)}; got {interval_seconds}",
        )
    spec = _INTERVALS[interval_seconds]

    dsn = os.getenv("SUPABASE_DB_URL")
    api_key = os.getenv("POLYGON_API_KEY")
    if not dsn:
        raise RuntimeError("SUPABASE_DB_URL is required")
    if not api_key:
        raise RuntimeError("POLYGON_API_KEY is required (sign up at https://polygon.io)")

    try:
        import httpx  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "httpx is required — add to pyproject.toml deps or `uv add httpx`",
        ) from exc

    backend = SupabaseBackend(dsn)
    writer = PersistenceWriter(backend)

    start_str = start.astimezone(UTC).strftime("%Y-%m-%d")
    end_str = end.astimezone(UTC).strftime("%Y-%m-%d")
    first_url = (
        f"{_POLYGON_BASE}/v2/aggs/ticker/{symbol.upper()}/range/"
        f"{spec.multiplier}/{spec.timespan}/{start_str}/{end_str}"
    )
    base_params: dict[str, Any] = {
        "adjusted": "true",
        "sort": "asc",
        "limit": _PAGE_LIMIT,
        "apiKey": api_key,
    }

    LOG.info(
        "fetching %s %s bars %s → %s (page limit=%d)",
        symbol, spec.timespan, start_str, end_str, _PAGE_LIMIT,
    )

    total_bars = 0
    page = 0
    next_url: str | None = first_url
    next_params: dict[str, Any] | None = base_params

    async with httpx.AsyncClient() as client:
        while next_url:
            page += 1
            payload = await _fetch_page(client, next_url, next_params)
            results = payload.get("results") or []
            if not results:
                LOG.info("page %d: 0 bars (no more data)", page)
                break
            bars = [_bar_from_polygon(symbol, interval_seconds, r) for r in results]
            await writer.write_bars(bars, feed=f"polygon_{spec.multiplier}{spec.timespan}")
            total_bars += len(bars)
            LOG.info(
                "page %d: %d bars (first=%s last=%s, total=%d)",
                page, len(bars),
                bars[0].open_time.isoformat(), bars[-1].open_time.isoformat(),
                total_bars,
            )

            # Polygon's next_url for pagination already encodes the cursor;
            # we just need to append the API key (it's stripped from next_url
            # for security).
            raw_next = payload.get("next_url")
            if raw_next:
                next_url = raw_next
                next_params = {"apiKey": api_key}
            else:
                next_url = None

    await backend.close()
    return {"pages": page, "bars": total_bars}


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=UTC)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Backfill historical bars from Polygon.io into Supabase.",
    )
    parser.add_argument("--symbol", default="QQQ", help="ticker (default: QQQ)")
    parser.add_argument(
        "--interval", type=int, default=60, choices=sorted(_INTERVALS),
        help="bar resolution in seconds (60/300/3600/86400)",
    )
    parser.add_argument(
        "--years", type=float, default=5.0,
        help="years of history to pull (default: 5); ignored if --start given",
    )
    parser.add_argument("--start", type=_parse_date, default=None)
    parser.add_argument("--end", type=_parse_date, default=None)
    args = parser.parse_args()

    end = args.end or datetime.now(tz=UTC)
    start = args.start or (end - timedelta(days=int(args.years * 365)))
    if start >= end:
        raise SystemExit("start must be < end")

    counts = asyncio.run(run(args.symbol, args.interval, start, end))
    LOG.info(
        "done: %d pages, %d bars persisted for %s @ %ds",
        counts["pages"], counts["bars"], args.symbol, args.interval,
    )


if __name__ == "__main__":
    main()
