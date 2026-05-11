"""One-shot driver that chains the IBKR bars backfill and the SMA/VWAP
signal backfill, configured entirely via env vars. This is the entrypoint
the ``backfill-worker`` Railway service runs — deploy the service and the
container pulls bars + computes crosses + exits.

Environment
-----------

``BACKFILL_SYMBOL``     — ticker (default ``QQQ``).
``BACKFILL_INTERVALS``  — space-separated bar-interval seconds
                          (default ``"60 300 3600 86400"``).
``BACKFILL_YEARS``      — how many years of history to attempt per
                          interval (default ``2``).
``BACKFILL_SMA_PERIOD`` — SMA period in bars for cross detection
                          (default ``9``).
``BACKFILL_SKIP_BARS``  — set to "1" to skip the IBKR pull and only
                          recompute signals from whatever bars already
                          exist in Supabase. Useful for iterating on the
                          indicator without re-pulling history.
``BACKFILL_SKIP_SIGNALS`` — set to "1" to pull bars only.

``IBKR_HOST`` / ``IBKR_PORT`` / ``IBKR_CLIENT_ID_BACKFILL`` flow through
to the bars backfill (defaults: ``ib-gateway.railway.internal`` / ``4004``
/ ``99``). ``SUPABASE_DB_URL`` is required.

Failure semantics
-----------------

If a single interval fails (e.g. IBKR pacing violation, gateway down,
empty depth), we log and continue to the next interval rather than
aborting the whole run. That way a partial backfill still produces
useful indicator data on the resolutions that did succeed.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta

from scripts import backfill_bars_ibkr, backfill_signals

LOG = logging.getLogger("alpha_kite.backfill_runner")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return int(raw)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return float(raw)


def _env_flag(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in ("1", "true", "yes", "on")


def _parse_intervals(raw: str) -> list[int]:
    parts = [p for p in raw.replace(",", " ").split() if p]
    seconds = [int(p) for p in parts]
    for s in seconds:
        if s not in backfill_bars_ibkr._INTERVALS:
            raise ValueError(
                f"unsupported interval {s}; allowed: "
                f"{sorted(backfill_bars_ibkr._INTERVALS)}",
            )
    return seconds


async def _run_one_interval(
    symbol: str,
    interval_seconds: int,
    years: float,
    sma_period: int,
    skip_bars: bool,
    skip_signals: bool,
    host: str,
    port: int,
    client_id: int,
) -> None:
    end_dt = datetime.now(tz=UTC)
    start_dt = end_dt - timedelta(days=int(years * 365))

    if not skip_bars:
        LOG.info("─── bars @ %ds — pulling %.1f years ───", interval_seconds, years)
        try:
            bars_counts = await backfill_bars_ibkr.run(
                symbol=symbol,
                interval_seconds=interval_seconds,
                start_dt=start_dt,
                end_dt=end_dt,
                host=host,
                port=port,
                client_id=client_id,
                max_requests=2000,
                pace_seconds=11.0,
                use_rth=True,
            )
            LOG.info(
                "bars @ %ds done: %d requests, %d bars",
                interval_seconds, bars_counts["requests"], bars_counts["bars"],
            )
        except Exception as exc:
            LOG.exception(
                "bars @ %ds failed (%s); continuing to next step",
                interval_seconds, exc,
            )
    else:
        LOG.info("BACKFILL_SKIP_BARS=1 — skipping IBKR pull at %ds", interval_seconds)

    if not skip_signals:
        LOG.info("─── signals @ %ds — computing %s crosses ───",
                 interval_seconds, f"SMA{sma_period}/VWAP")
        try:
            sig_counts = await backfill_signals.run(
                symbol=symbol,
                interval_seconds=interval_seconds,
                start_dt=start_dt,
                end_dt=end_dt,
                sma_period=sma_period,
            )
            LOG.info(
                "signals @ %ds done: scanned %d bars, wrote %d crosses, purged %d",
                interval_seconds, sig_counts["bars"], sig_counts["crosses"],
                sig_counts["deleted"],
            )
        except Exception as exc:
            LOG.exception("signals @ %ds failed (%s)", interval_seconds, exc)
    else:
        LOG.info("BACKFILL_SKIP_SIGNALS=1 — skipping signal backfill at %ds",
                 interval_seconds)


async def main_async() -> None:
    symbol = os.getenv("BACKFILL_SYMBOL", "QQQ")
    intervals = _parse_intervals(os.getenv("BACKFILL_INTERVALS", "60 300 3600 86400"))
    years = _env_float("BACKFILL_YEARS", 2.0)
    sma_period = _env_int("BACKFILL_SMA_PERIOD", 9)
    skip_bars = _env_flag("BACKFILL_SKIP_BARS")
    skip_signals = _env_flag("BACKFILL_SKIP_SIGNALS")
    host = os.getenv("IBKR_HOST", "ib-gateway.railway.internal")
    port = _env_int("IBKR_PORT", 4004)
    client_id = _env_int("IBKR_CLIENT_ID_BACKFILL", 99)

    LOG.info(
        "starting backfill: symbol=%s intervals=%s years=%.1f sma=%d "
        "ibkr=%s:%d skip_bars=%s skip_signals=%s",
        symbol, intervals, years, sma_period, host, port, skip_bars, skip_signals,
    )

    for s in intervals:
        await _run_one_interval(
            symbol=symbol,
            interval_seconds=s,
            years=years,
            sma_period=sma_period,
            skip_bars=skip_bars,
            skip_signals=skip_signals,
            host=host,
            port=port,
            client_id=client_id,
        )

    LOG.info("backfill_runner finished")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
