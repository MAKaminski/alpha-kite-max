"""Round-trip integration tests against a real Postgres / Supabase stack.

These tests are marked `supabase` so the default CI skips them. To run
locally, start the Supabase local stack, apply
`infra/supabase/migrations/0001_initial.sql`, then:

    SUPABASE_DB_URL=postgresql://postgres:postgres@localhost:54322/postgres \\
      pytest -m supabase tests/test_persistence
"""

from __future__ import annotations

import os
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from contracts.broker import (
    Fill,
    OrderIntent,
    OrderSide,
    OrderType,
    Position,
)
from contracts.data_feed import Bar, Quote
from contracts.strategy import Signal, SignalDirection
from services.persistence import (
    AuditEvent,
    PersistenceReader,
    PersistenceWriter,
    SupabaseBackend,
)

pytestmark = pytest.mark.supabase


def _require_dsn() -> str:
    dsn = os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        pytest.skip("SUPABASE_DB_URL not set; skipping Supabase integration test")
    return dsn


@pytest.mark.asyncio
async def test_supabase_round_trip() -> None:
    dsn = _require_dsn()
    backend = SupabaseBackend(dsn=dsn)
    writer = PersistenceWriter(backend)
    reader = PersistenceReader(backend)

    try:
        ts = datetime.now(UTC)
        symbol = f"TEST-{uuid4().hex[:6]}"

        quote = Quote(
            symbol=symbol,
            timestamp=ts,
            bid=Decimal("100.00"),
            ask=Decimal("100.05"),
        )
        bar = Bar(
            symbol=symbol,
            interval_seconds=60,
            open_time=ts,
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99.5"),
            close=Decimal("100.5"),
            volume=10,
        )
        signal = Signal(
            name="integration_test",
            direction=SignalDirection.LONG_VOL_UP,
            timestamp=ts,
            symbol=symbol,
        )
        intent = OrderIntent(
            intent_id=uuid4(),
            created_at=ts,
            symbol=symbol,
            is_option=False,
            side=OrderSide.BUY,
            quantity=1,
            order_type=OrderType.MARKET,
        )
        fill = Fill(
            fill_id=f"F-{uuid4().hex[:6]}",
            intent_id=intent.intent_id,
            broker_order_id=f"B-{uuid4().hex[:6]}",
            timestamp=ts,
            symbol=symbol,
            is_option=False,
            side=OrderSide.BUY,
            quantity=1,
            price=Decimal("100.50"),
        )
        position = Position(
            symbol=symbol,
            is_option=False,
            quantity=1,
            avg_cost=Decimal("100.50"),
        )
        audit = AuditEvent(
            ts=ts,
            actor="engine",
            event_type="INTEGRATION_TEST",
            severity="INFO",
            message="round trip",
            payload={"symbol": symbol},
        )

        await writer.write_tick(quote, feed="integration")
        await writer.write_bar(bar, feed="integration")
        await writer.write_bar(bar, feed="integration")  # idempotent
        await writer.write_signal(signal)
        await writer.write_order_intent(intent, dry_run=True)
        await writer.write_order_intent(intent, dry_run=True)  # idempotent
        await writer.write_fill(fill)
        await writer.write_fill(fill)  # idempotent
        await writer.write_position(position)
        await writer.write_position(position)  # idempotent
        await writer.write_audit(audit)
        await writer.bump_daily_pnl(date.today(), Decimal("1.00"), win=True)

        ticks = await backend.select("ticks", where={"symbol": symbol})
        assert len(ticks) >= 1

        bars = await backend.select(
            "bars",
            where={"symbol": symbol, "interval_seconds": 60},
        )
        assert len(bars) == 1

        intents = await backend.select(
            "order_intents", where={"intent_id": str(intent.intent_id)}
        )
        assert len(intents) == 1

        fills = await backend.select("fills", where={"fill_id": fill.fill_id})
        assert len(fills) == 1

        signals_recent = await reader.recent_signals(limit=200)
        assert any(s["symbol"] == symbol for s in signals_recent)

        positions_open = await reader.open_positions()
        assert any(p["symbol"] == symbol for p in positions_open)
    finally:
        await backend.close()
