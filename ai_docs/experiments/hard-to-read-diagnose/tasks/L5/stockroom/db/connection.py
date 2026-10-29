"""Opening the stockroom database."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from stockroom.config import Settings, get_settings
from stockroom.db import migrations
from stockroom.domain.errors import StockroomError


def connect(path: Path | str, *, busy_timeout_ms: int = 2000, migrate: bool = True) -> sqlite3.Connection:
    """Open an existing database and bring its schema up to date.

    The database is never created here: a missing file almost always means
    a wrong path, and silently creating an empty database would make every
    report come back blank instead of failing loudly.
    """
    path = Path(path)
    if not path.exists():
        raise StockroomError(f"database not found: {path}")

    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(f"PRAGMA busy_timeout = {int(busy_timeout_ms)}")

    if migrate:
        migrations.apply(conn)
    return conn


def open_default(settings: Settings | None = None) -> sqlite3.Connection:
    settings = settings or get_settings()
    return connect(settings.db_path, busy_timeout_ms=settings.busy_timeout_ms)
