"""Explicit transaction control.

Connections are opened in autocommit mode (``isolation_level=None``) so that
nothing is ever committed implicitly; every write goes through
:func:`transaction`. Nested use joins the outer transaction.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator


@contextmanager
def transaction(conn: sqlite3.Connection, *, immediate: bool = True) -> Iterator[sqlite3.Connection]:
    if conn.in_transaction:
        yield conn
        return
    conn.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")
