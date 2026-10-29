"""Sales orders and their lines."""

from __future__ import annotations

import sqlite3
from datetime import date

from stockroom.domain.errors import NotFound
from stockroom.domain.models import Order, OrderLine
from stockroom.utils.dates import as_date

ORDER_PREFIX = "SO-"


def next_number(conn: sqlite3.Connection) -> str:
    conn.execute("INSERT OR IGNORE INTO counters (name, value) VALUES ('order', 1000)")
    conn.execute("UPDATE counters SET value = value + 1 WHERE name = 'order'")
    value = conn.execute("SELECT value FROM counters WHERE name = 'order'").fetchone()[0]
    return f"{ORDER_PREFIX}{int(value)}"


def normalize_number(number: str) -> str:
    number = number.strip().upper()
    if number.isdigit():
        number = ORDER_PREFIX + number
    return number


def insert_order(conn: sqlite3.Connection, number: str, customer: str, warehouse: str, order_date: date) -> None:
    conn.execute(
        "INSERT INTO orders (number, customer, warehouse, status, order_date) VALUES (?, ?, ?, 'open', ?)",
        (number, customer, warehouse, order_date.isoformat()),
    )


def insert_line(conn: sqlite3.Connection, line: OrderLine) -> int:
    cur = conn.execute(
        "INSERT INTO order_lines (order_number, line_no, sku, qty, shipped_qty, price_cents, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (line.order_number, line.line_no, line.sku, line.qty, line.shipped_qty, line.price_cents, line.status),
    )
    return int(cur.lastrowid)


def _line(row: sqlite3.Row) -> OrderLine:
    return OrderLine(
        id=int(row["id"]),
        order_number=row["order_number"],
        line_no=int(row["line_no"]),
        sku=row["sku"],
        qty=int(row["qty"]),
        shipped_qty=int(row["shipped_qty"]),
        price_cents=int(row["price_cents"]),
        status=row["status"],
    )


def get_lines(conn: sqlite3.Connection, number: str) -> list[OrderLine]:
    return [
        _line(r)
        for r in conn.execute(
            "SELECT id, order_number, line_no, sku, qty, shipped_qty, price_cents, status "
            "FROM order_lines WHERE order_number = ? ORDER BY line_no",
            (number,),
        )
    ]


def get(conn: sqlite3.Connection, number: str) -> Order:
    number = normalize_number(number)
    row = conn.execute(
        "SELECT number, customer, warehouse, status, order_date, updated_at FROM orders WHERE number = ?",
        (number,),
    ).fetchone()
    if row is None:
        raise NotFound(f"unknown order {number!r}")
    return Order(
        number=row["number"],
        customer=row["customer"],
        warehouse=row["warehouse"],
        status=row["status"],
        order_date=as_date(row["order_date"]),
        lines=get_lines(conn, number),
        updated_at=row["updated_at"],
    )


def add_shipped(conn: sqlite3.Connection, line_id: int, qty: int) -> None:
    conn.execute("UPDATE order_lines SET shipped_qty = shipped_qty + ? WHERE id = ?", (int(qty), line_id))


def set_line_status(conn: sqlite3.Connection, line_id: int, status: str) -> None:
    conn.execute("UPDATE order_lines SET status = ? WHERE id = ?", (status, line_id))


def set_status(conn: sqlite3.Connection, number: str, status: str) -> None:
    conn.execute("UPDATE orders SET status = ? WHERE number = ?", (status, number))


def open_lines(conn: sqlite3.Connection, *, warehouse: str | None = None, sku: str | None = None) -> list[tuple[Order, OrderLine]]:
    sql = (
        "SELECT o.number, o.customer, o.warehouse, o.status AS order_status, o.order_date, "
        "       l.id, l.order_number, l.line_no, l.sku, l.qty, l.shipped_qty, l.price_cents, l.status "
        "  FROM order_lines l JOIN orders o ON o.number = l.order_number "
        " WHERE l.status = 'open' AND l.qty > l.shipped_qty"
    )
    params: list[object] = []
    if warehouse:
        sql += " AND o.warehouse = ?"
        params.append(warehouse)
    if sku:
        sql += " AND l.sku = ?"
        params.append(sku)
    sql += " ORDER BY o.order_date, o.number, l.line_no"
    result = []
    for r in conn.execute(sql, params):
        order = Order(
            number=r["number"],
            customer=r["customer"],
            warehouse=r["warehouse"],
            status=r["order_status"],
            order_date=as_date(r["order_date"]),
        )
        result.append((order, _line(r)))
    return result


def list_orders(conn: sqlite3.Connection, *, status: str | None = None) -> list[Order]:
    sql = "SELECT number FROM orders"
    params: list[object] = []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    sql += " ORDER BY number"
    return [get(conn, r["number"]) for r in conn.execute(sql, params).fetchall()]
