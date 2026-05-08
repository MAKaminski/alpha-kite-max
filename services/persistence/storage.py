"""Storage backend abstraction.

Two backends are supplied:
  * `InMemoryBackend` — pure-Python; fast; used by tests and dry-run.
  * `SupabaseBackend` — talks to Postgres via asyncpg using parameterized
    SQL. No ORM. Connection URL comes from the SUPABASE_DB_URL env var.

Backends speak in `dict[str, Any]` rows. The writer is responsible for
turning Pydantic / dataclass models into row dicts before calling
`insert` / `upsert`.
"""

from __future__ import annotations

import os
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    """Minimal Postgres-flavored CRUD that the writer/reader rely on."""

    async def insert(self, table: str, rows: list[dict[str, Any]]) -> None:
        """Append-only insert. No conflict resolution."""
        ...

    async def upsert(
        self,
        table: str,
        rows: list[dict[str, Any]],
        conflict_columns: list[str],
    ) -> None:
        """Insert-or-update using `conflict_columns` as the conflict target."""
        ...

    async def select(
        self,
        table: str,
        where: dict[str, Any] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Equality-only filtering. Returns row dicts."""
        ...


# ──────────────────────────────────────────────────────────────────────────
# In-memory backend
# ──────────────────────────────────────────────────────────────────────────


def _matches(row: dict[str, Any], where: dict[str, Any] | None) -> bool:
    if not where:
        return True
    for k, v in where.items():
        if row.get(k) != v:
            return False
    return True


def _parse_order_by(order_by: str) -> tuple[str, bool]:
    """Returns (column, descending)."""
    parts = order_by.strip().split()
    col = parts[0]
    desc = len(parts) > 1 and parts[1].upper() == "DESC"
    return col, desc


class InMemoryBackend:
    """Dict-of-table → list[row] backend with proper conflict-resolution upsert."""

    def __init__(self) -> None:
        self._tables: dict[str, list[dict[str, Any]]] = {}

    def _table(self, name: str) -> list[dict[str, Any]]:
        return self._tables.setdefault(name, [])

    async def insert(self, table: str, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        bucket = self._table(table)
        for row in rows:
            bucket.append(dict(row))

    async def upsert(
        self,
        table: str,
        rows: list[dict[str, Any]],
        conflict_columns: list[str],
    ) -> None:
        if not rows:
            return
        bucket = self._table(table)
        for row in rows:
            row = dict(row)
            replaced = False
            for i, existing in enumerate(bucket):
                if all(existing.get(c) == row.get(c) for c in conflict_columns):
                    merged = {**existing, **row}
                    bucket[i] = merged
                    replaced = True
                    break
            if not replaced:
                bucket.append(row)

    async def select(
        self,
        table: str,
        where: dict[str, Any] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        bucket = self._tables.get(table, [])
        rows = [dict(r) for r in bucket if _matches(r, where)]
        if order_by:
            col, desc = _parse_order_by(order_by)
            rows.sort(key=lambda r: (r.get(col) is None, r.get(col)), reverse=desc)
        if limit is not None:
            rows = rows[:limit]
        return rows


# ──────────────────────────────────────────────────────────────────────────
# Supabase / Postgres backend (asyncpg)
# ──────────────────────────────────────────────────────────────────────────


class SupabaseBackend:
    """Postgres backend that uses `asyncpg` directly with parameterized SQL."""

    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = dsn or os.environ.get("SUPABASE_DB_URL")
        if not self._dsn:
            raise RuntimeError(
                "SupabaseBackend requires SUPABASE_DB_URL env var or explicit dsn arg"
            )
        # We import asyncpg lazily so that importing this module never fails
        # in environments without the package available.
        import asyncpg  # noqa: F401  (side-effect-free import-time check)

        self._pool: Any = None

    async def _ensure_pool(self) -> Any:
        if self._pool is None:
            import asyncpg
            import json

            async def _init_conn(conn: Any) -> None:
                # Register Python dict <-> JSONB/JSON codecs. Without this,
                # asyncpg sees a dict for a JSONB column and raises
                # "expected str, got dict".
                for type_name in ("jsonb", "json"):
                    await conn.set_type_codec(
                        type_name,
                        encoder=json.dumps,
                        decoder=json.loads,
                        schema="pg_catalog",
                    )

            self._pool = await asyncpg.create_pool(self._dsn, init=_init_conn)
        return self._pool

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @staticmethod
    def _placeholders(start: int, count: int) -> str:
        return ", ".join(f"${i}" for i in range(start, start + count))

    async def insert(self, table: str, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        pool = await self._ensure_pool()
        cols = list(rows[0].keys())
        col_sql = ", ".join(f'"{c}"' for c in cols)
        async with pool.acquire() as conn:
            for row in rows:
                values = [row.get(c) for c in cols]
                ph = self._placeholders(1, len(cols))
                sql = f'INSERT INTO "{table}" ({col_sql}) VALUES ({ph})'
                await conn.execute(sql, *values)

    async def upsert(
        self,
        table: str,
        rows: list[dict[str, Any]],
        conflict_columns: list[str],
    ) -> None:
        if not rows:
            return
        pool = await self._ensure_pool()
        cols = list(rows[0].keys())
        col_sql = ", ".join(f'"{c}"' for c in cols)
        conflict_sql = ", ".join(f'"{c}"' for c in conflict_columns)
        update_cols = [c for c in cols if c not in conflict_columns]
        if update_cols:
            set_sql = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in update_cols)
            on_conflict = f"ON CONFLICT ({conflict_sql}) DO UPDATE SET {set_sql}"
        else:
            on_conflict = f"ON CONFLICT ({conflict_sql}) DO NOTHING"
        async with pool.acquire() as conn:
            for row in rows:
                values = [row.get(c) for c in cols]
                ph = self._placeholders(1, len(cols))
                sql = (
                    f'INSERT INTO "{table}" ({col_sql}) VALUES ({ph}) {on_conflict}'
                )
                await conn.execute(sql, *values)

    async def select(
        self,
        table: str,
        where: dict[str, Any] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        pool = await self._ensure_pool()
        sql = f'SELECT * FROM "{table}"'
        values: list[Any] = []
        if where:
            clauses = []
            for i, (k, v) in enumerate(where.items(), start=1):
                clauses.append(f'"{k}" = ${i}')
                values.append(v)
            sql += " WHERE " + " AND ".join(clauses)
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        async with pool.acquire() as conn:
            records = await conn.fetch(sql, *values)
        return [dict(r) for r in records]


__all__ = ["InMemoryBackend", "StorageBackend", "SupabaseBackend"]
