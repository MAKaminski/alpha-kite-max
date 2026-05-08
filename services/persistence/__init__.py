"""Persistence layer: pluggable storage backend + writer + reader.

The writer is called from the engine when events happen; the reader
powers the dashboard. Both rely on a `StorageBackend` so that tests
can run against an in-memory store and production runs against
Supabase/Postgres.
"""

from __future__ import annotations

from services.persistence.models import AuditEvent, DailyPnlRow
from services.persistence.reader import PersistenceReader
from services.persistence.storage import (
    InMemoryBackend,
    StorageBackend,
    SupabaseBackend,
)
from services.persistence.writer import PersistenceWriter

__all__ = [
    "AuditEvent",
    "DailyPnlRow",
    "InMemoryBackend",
    "PersistenceReader",
    "PersistenceWriter",
    "StorageBackend",
    "SupabaseBackend",
]
