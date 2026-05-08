"""Live smoke test for `IBKRPaperBroker`.

This test is marked `@pytest.mark.live` and is skipped in CI by default. It
documents how to run an end-to-end paper-trade against a real IBKR Gateway:

  1. Start TWS or IB Gateway in paper-trading mode and log in with a DU*
     account.
  2. In API → Settings, enable the API and ensure the host/port match
     (`127.0.0.1:7497` is the default for paper TWS).
  3. From the repo root::

       pytest tests/test_broker/test_ibkr_paper_smoke.py -m live -v

The test connects, fetches account summary, then disconnects. It does NOT
place any orders to keep the smoke run idempotent.
"""

from __future__ import annotations

import os

import pytest
from engine.broker import IBKRPaperBroker

pytestmark = pytest.mark.live


@pytest.mark.asyncio
async def test_connect_and_fetch_account_summary_against_real_gateway() -> None:
    host = os.environ.get("IB_HOST", "127.0.0.1")
    port = int(os.environ.get("IB_PORT", "7497"))
    client_id = int(os.environ.get("IB_CLIENT_ID", "17"))

    broker = IBKRPaperBroker(
        host=host,
        port=port,
        client_id=client_id,
        dry_run=False,
        paper_account_allowlist=["DEMO", "PAPER"],
    )
    try:
        await broker.connect()
        summary = await broker.get_account_summary()
        assert summary.account_id
        # Defense in depth: even if the test runner forgets the env vars, the
        # gateway must not be a live account.
        assert summary.account_id.upper().startswith("DU") or summary.account_type.value in {
            "PAPER",
            "DEMO",
        }
    finally:
        await broker.disconnect()
