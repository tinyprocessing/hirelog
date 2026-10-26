"""Postgres pool and a tiny forward-only migrator (files in app/migrations, applied in name order)."""
from __future__ import annotations

import logging
from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from .config import settings

log = logging.getLogger("hirelog.db")
pool = AsyncConnectionPool(settings.database_url, min_size=1, max_size=10, open=False,
                           kwargs={"row_factory": dict_row, "autocommit": True})


async def migrate() -> None:
    async with pool.connection() as c:
        await c.execute("SELECT pg_advisory_lock(4242)")   # several workers start at once
        try:
            await _migrate(c)
        finally:
            await c.execute("SELECT pg_advisory_unlock(4242)")


async def _migrate(c) -> None:
    await c.execute("CREATE TABLE IF NOT EXISTS schema_migration (name text PRIMARY KEY, at timestamptz DEFAULT now())")
    done = {r["name"] for r in await (await c.execute("SELECT name FROM schema_migration")).fetchall()}
    for f in sorted((Path(__file__).parent / "migrations").glob("*.sql")):
        if f.name in done:
            continue
        log.info("migrating %s", f.name)
        async with c.transaction():
            await c.execute(f.read_text())
            await c.execute("INSERT INTO schema_migration (name) VALUES (%s)", (f.name,))


async def fetch(sql: str, *args) -> list[dict]:
    async with pool.connection() as c:
        return await (await c.execute(sql, args or None)).fetchall()


async def fetchone(sql: str, *args) -> dict | None:
    async with pool.connection() as c:
        return await (await c.execute(sql, args or None)).fetchone()


async def execute(sql: str, *args) -> None:
    async with pool.connection() as c:
        await c.execute(sql, args or None)
