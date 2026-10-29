"""Customer master data."""

from __future__ import annotations

import sqlite3

from stockroom.domain.errors import NotFound
from stockroom.domain.models import Customer


def _customer(row: sqlite3.Row) -> Customer:
    return Customer(
        code=row["code"],
        name=row["name"],
        allow_backorder=bool(row["allow_backorder"]),
        credit_limit_cents=int(row["credit_limit_cents"]),
    )


def get(conn: sqlite3.Connection, code: str) -> Customer:
    row = conn.execute(
        "SELECT code, name, allow_backorder, credit_limit_cents FROM customers WHERE code = ?",
        (code.strip().upper(),),
    ).fetchone()
    if row is None:
        raise NotFound(f"unknown customer {code!r}")
    return _customer(row)


def list_customers(conn: sqlite3.Connection) -> list[Customer]:
    return [
        _customer(r)
        for r in conn.execute(
            "SELECT code, name, allow_backorder, credit_limit_cents FROM customers ORDER BY code"
        )
    ]


def open_balance_cents(conn: sqlite3.Connection, code: str) -> int:
    """Value of everything ordered but not yet shipped for a customer."""
    row = conn.execute(
        """
        SELECT COALESCE(SUM((l.qty - l.shipped_qty) * l.price_cents), 0)
          FROM order_lines l
          JOIN orders o ON o.number = l.order_number
         WHERE o.customer = ? AND l.status = 'open'
        """,
        (code,),
    ).fetchone()
    return int(row[0])
