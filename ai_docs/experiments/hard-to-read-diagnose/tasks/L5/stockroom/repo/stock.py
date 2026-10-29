"""Per-warehouse stock levels.

``stock_levels`` keeps two running counters per SKU and warehouse:

* ``on_hand``  - physical units on the shelf
* ``reserved`` - units promised to open order lines (may exceed on_hand
  for customers who accept backorders)

Writers only ever apply deltas, so concurrent sessions cannot lose each
other's updates.
"""

from __future__ import annotations

import sqlite3

from stockroom.domain.models import AvailabilityRow, StockLevel


def _level(row: sqlite3.Row) -> StockLevel:
    return StockLevel(
        sku=row["sku"],
        warehouse=row["warehouse"],
        on_hand=int(row["on_hand"]),
        reserved=int(row["reserved"]),
        updated_at=row["updated_at"],
    )


def ensure_level(conn: sqlite3.Connection, sku: str, warehouse: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO stock_levels (sku, warehouse, on_hand, reserved) VALUES (?, ?, 0, 0)",
        (sku, warehouse),
    )


def get_level(conn: sqlite3.Connection, sku: str, warehouse: str) -> StockLevel:
    row = conn.execute(
        "SELECT sku, warehouse, on_hand, reserved, updated_at FROM stock_levels "
        "WHERE sku = ? AND warehouse = ?",
        (sku, warehouse),
    ).fetchone()
    if row is None:
        return StockLevel(sku=sku, warehouse=warehouse, on_hand=0, reserved=0)
    return _level(row)


def apply_delta(
    conn: sqlite3.Connection,
    sku: str,
    warehouse: str,
    *,
    on_hand: int = 0,
    reserved: int = 0,
) -> StockLevel:
    """Add ``on_hand`` and ``reserved`` to the counters and return the new level."""
    ensure_level(conn, sku, warehouse)
    conn.execute(
        "UPDATE stock_levels SET on_hand = on_hand + ?, reserved = reserved + ? "
        "WHERE sku = ? AND warehouse = ?",
        (int(on_hand), int(reserved), sku, warehouse),
    )
    return get_level(conn, sku, warehouse)


def levels_for_sku(conn: sqlite3.Connection, sku: str) -> list[StockLevel]:
    return [
        _level(r)
        for r in conn.execute(
            "SELECT sku, warehouse, on_hand, reserved, updated_at FROM stock_levels "
            "WHERE sku = ? ORDER BY warehouse",
            (sku,),
        )
    ]


def total_on_hand(conn: sqlite3.Connection, sku: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(on_hand), 0) FROM stock_levels WHERE sku = ?", (sku,)
    ).fetchone()
    return int(row[0])


def list_availability(
    conn: sqlite3.Connection,
    *,
    sku: str | None = None,
    warehouse: str | None = None,
) -> list[AvailabilityRow]:
    sql = (
        "SELECT sku, name, warehouse, on_hand, reserved, reorder_point, reorder_qty "
        "FROM v_availability WHERE 1 = 1"
    )
    params: list[object] = []
    if sku:
        sql += " AND sku = ?"
        params.append(sku)
    if warehouse:
        sql += " AND warehouse = ?"
        params.append(warehouse)
    sql += " ORDER BY sku, warehouse"
    return [
        AvailabilityRow(
            sku=r["sku"],
            name=r["name"],
            warehouse=r["warehouse"],
            on_hand=int(r["on_hand"]),
            reserved=int(r["reserved"]),
            reorder_point=int(r["reorder_point"]),
            reorder_qty=int(r["reorder_qty"]),
        )
        for r in conn.execute(sql, params)
    ]
