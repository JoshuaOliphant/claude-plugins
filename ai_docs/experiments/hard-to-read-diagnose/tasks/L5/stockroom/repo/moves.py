"""The stock movement journal (append-only)."""

from __future__ import annotations

import sqlite3
from datetime import date

from stockroom.domain.models import StockMove
from stockroom.utils.dates import as_date

KINDS = ("receipt", "ship", "adjust", "transfer_out", "transfer_in")


def record(
    conn: sqlite3.Connection,
    *,
    sku: str,
    warehouse: str,
    kind: str,
    qty: int,
    moved_on: date,
    reference: str | None = None,
    unit_cost_cents: int | None = None,
) -> int:
    if kind not in KINDS:
        raise ValueError(f"unknown move kind {kind!r}")
    cur = conn.execute(
        "INSERT INTO stock_moves (sku, warehouse, kind, qty, reference, unit_cost_cents, moved_on) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (sku, warehouse, kind, int(qty), reference, unit_cost_cents, moved_on.isoformat()),
    )
    return int(cur.lastrowid)


def list_moves(
    conn: sqlite3.Connection,
    *,
    sku: str | None = None,
    warehouse: str | None = None,
    since: date | None = None,
) -> list[StockMove]:
    sql = (
        "SELECT id, sku, warehouse, kind, qty, reference, unit_cost_cents, moved_on "
        "FROM stock_moves WHERE 1 = 1"
    )
    params: list[object] = []
    if sku:
        sql += " AND sku = ?"
        params.append(sku)
    if warehouse:
        sql += " AND warehouse = ?"
        params.append(warehouse)
    if since:
        sql += " AND moved_on >= ?"
        params.append(since.isoformat())
    sql += " ORDER BY moved_on, id"
    return [
        StockMove(
            id=int(r["id"]),
            sku=r["sku"],
            warehouse=r["warehouse"],
            kind=r["kind"],
            qty=int(r["qty"]),
            reference=r["reference"],
            unit_cost_cents=r["unit_cost_cents"],
            moved_on=as_date(r["moved_on"]),
        )
        for r in conn.execute(sql, params)
    ]


def net_quantity(conn: sqlite3.Connection, sku: str, warehouse: str) -> int:
    """Sum of all journal entries; should equal ``stock_levels.on_hand``."""
    row = conn.execute(
        "SELECT COALESCE(SUM(qty), 0) FROM stock_moves WHERE sku = ? AND warehouse = ?",
        (sku, warehouse),
    ).fetchone()
    return int(row[0])
