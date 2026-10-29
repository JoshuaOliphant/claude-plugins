"""Forward-only schema migrations.

Versions 1-6 were squashed into the baseline database that ships in
``data/stockroom.db``; only changes made after the squash live here. Each
migration runs once, inside its own transaction, and is recorded in
``schema_version``.
"""

from __future__ import annotations

import sqlite3
from typing import Callable

from stockroom.db.transaction import transaction
from stockroom.utils.dates import timestamp

BASELINE_VERSION = 6

Migration = tuple[int, str, Callable[[sqlite3.Connection], None]]


def current_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return int(row[0]) if row and row[0] is not None else BASELINE_VERSION


def _m7_indexes(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE INDEX IF NOT EXISTS idx_order_lines_sku ON order_lines (sku, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_stock_moves_sku ON stock_moves (sku, moved_on)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders (customer, status)")


def _m8_legacy_cleanup(conn: sqlite3.Connection) -> None:
    # The v5 spreadsheet importer could leave negative reservations and
    # lower-case SKUs behind.
    conn.execute("UPDATE stock_levels SET reserved = 0 WHERE reserved < 0")
    conn.execute("UPDATE products SET sku = UPPER(sku) WHERE sku <> UPPER(sku)")


def _m9_availability_view(conn: sqlite3.Connection) -> None:
    conn.execute("DROP VIEW IF EXISTS v_availability")
    conn.execute(
        """
        CREATE VIEW v_availability AS
        SELECT p.sku                    AS sku,
               p.name                   AS name,
               w.code                   AS warehouse,
               COALESCE(s.on_hand, 0)   AS on_hand,
               COALESCE(s.reserved, 0)  AS reserved,
               p.reorder_point          AS reorder_point,
               p.reorder_qty            AS reorder_qty
          FROM products p
         CROSS JOIN warehouses w
          LEFT JOIN stock_levels s
                 ON s.sku = p.sku AND s.warehouse = w.code
         WHERE p.active = 1
        """
    )


MIGRATIONS: list[Migration] = [
    (7, "indexes for order and move lookups", _m7_indexes),
    (8, "clean up rows left by the v5 importer", _m8_legacy_cleanup),
    (9, "availability view", _m9_availability_view),
]


def pending(conn: sqlite3.Connection) -> list[Migration]:
    version = current_version(conn)
    return [m for m in MIGRATIONS if m[0] > version]


def apply(conn: sqlite3.Connection) -> list[int]:
    applied = []
    for version, description, step in pending(conn):
        with transaction(conn):
            step(conn)
            conn.execute(
                "INSERT INTO schema_version (version, applied_at, description) VALUES (?, ?, ?)",
                (version, timestamp(), description),
            )
        applied.append(version)
    return applied
