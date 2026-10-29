"""Remember which tickets were already notified so re-runs don't spam."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path

from ..utils.timeutil import format_iso, utcnow

_SCHEMA = """
CREATE TABLE IF NOT EXISTS delivered (
    ticket_id TEXT PRIMARY KEY,
    channel   TEXT NOT NULL,
    batch     INTEGER NOT NULL,
    at        TEXT NOT NULL
)
"""


class DeliveryState:
    def __init__(self, path: Path, readonly: bool = False):
        self.path = path
        self.readonly = readonly
        self._conn: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection | None:
        if self._conn is None:
            if self.readonly:
                if not self.path.exists():
                    return None
                self._conn = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
            else:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self._conn = sqlite3.connect(self.path)
                self._conn.execute(_SCHEMA)
        return self._conn

    def delivered_ids(self) -> set[str]:
        conn = self._connect()
        if conn is None:
            return set()
        try:
            return {row[0] for row in conn.execute("SELECT ticket_id FROM delivered")}
        except sqlite3.OperationalError:
            return set()

    def mark(self, ticket_ids: Iterable[str], channel: str, batch: int) -> None:
        if self.readonly:
            return
        conn = self._connect()
        assert conn is not None
        at = format_iso(utcnow())
        with conn:
            conn.executemany(
                "INSERT OR REPLACE INTO delivered (ticket_id, channel, batch, at) "
                "VALUES (?, ?, ?, ?)",
                [(tid, channel, batch, at) for tid in ticket_ids],
            )

    def forget(self) -> int:
        conn = self._connect()
        if conn is None or self.readonly:
            return 0
        with conn:
            return conn.execute("DELETE FROM delivered").rowcount

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
