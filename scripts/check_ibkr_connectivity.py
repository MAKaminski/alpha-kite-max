"""Manual connectivity check for the IBKR paper-trading test suite.

Usage::

    uv run python -m scripts.check_ibkr_connectivity

    # Or against a non-default gateway / proxy:
    IB_HOST=shortline.proxy.rlwy.net IB_PORT=50990 \
        uv run python -m scripts.check_ibkr_connectivity

Runs four bounded checks in sequence and exits 0 only if all pass:

  1. Account summary fetch (proves the API handshake completes)
  2. DU* paper-account validation (prevents accidental live trading)
  3. ``Stock("QQQ")`` qualification (proves symbol resolution works)
  4. Disconnect (proves clean teardown)

Designed to be a *fast* (≈3-5 seconds) sanity check the user can run
before invoking the full pytest suite — surface a connection problem
in 5 seconds instead of waiting on pytest startup + 6 test setups.

The exit code maps to which test layer would fail:

  0 — All checks passed. Layer 2 & 3 will at least connect.
  1 — Could not even reach the gateway. Layer 2 will skip ALL.
  2 — Connected but account is non-paper. Layer 2 will FAIL fast.
  3 — Connected but contract qualification fails. Layer 2 mid-suite fail.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from engine.broker import IBKRPaperBroker

LOG = logging.getLogger("alpha_kite.check_ibkr")


async def _check() -> int:
    host = os.environ.get("IB_HOST", "127.0.0.1")
    port = int(os.environ.get("IB_PORT", "4002"))
    client_id = int(os.environ.get("IB_CLIENT_ID", "30"))

    LOG.info("connecting to %s:%s (clientId=%s, dry_run=False)", host, port, client_id)
    broker = IBKRPaperBroker(
        host=host, port=port, client_id=client_id,
        dry_run=False, paper_account_allowlist=["DEMO", "PAPER"],
    )

    try:
        await broker.connect()
    except Exception as exc:
        LOG.error("CONNECT FAILED: %s", exc)
        LOG.error("→ Layer 2 / Layer 3 tests will be SKIPPED. Fix the gateway first.")
        return 1

    try:
        summary = await broker.get_account_summary()
        LOG.info(
            "connected: account_id=%s account_type=%s nav=%s",
            summary.account_id, summary.account_type.value, summary.net_liquidation,
        )

        if not summary.account_id.startswith("DU"):
            LOG.error(
                "ACCOUNT IS NOT PAPER: %r — refusing to proceed. "
                "Layer 2 would fast-fail with the same message.",
                summary.account_id,
            )
            return 2

        # Qualify a QQQ stock contract to verify symbol-resolution path.
        try:
            from ib_insync import Stock  # type: ignore[import-not-found]
            qualified = await broker.ib.qualifyContractsAsync(
                Stock("QQQ", "SMART", "USD"),
            )
            if not qualified or not int(getattr(qualified[0], "conId", 0) or 0):
                LOG.error(
                    "QUALIFY FAILED: QQQ stock contract returned no conId. "
                    "Layer 2 contract tests will fail.",
                )
                return 3
            LOG.info(
                "qualified QQQ: conId=%s exchange=%s",
                qualified[0].conId, qualified[0].exchange,
            )
        except Exception as exc:
            LOG.error("QUALIFY FAILED: %s", exc)
            return 3

        LOG.info("✓ all checks passed — Layer 2 / 3 tests should run cleanly")
        return 0
    finally:
        try:
            await broker.disconnect()
        except Exception:
            pass


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )
    code = asyncio.run(_check())
    sys.exit(code)


if __name__ == "__main__":
    main()
