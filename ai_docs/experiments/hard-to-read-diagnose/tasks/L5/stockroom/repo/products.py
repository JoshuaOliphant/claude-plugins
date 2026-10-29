"""Products and warehouses (the reference data)."""

from __future__ import annotations

import sqlite3

from stockroom.domain.errors import NotFound
from stockroom.domain.models import Product, Warehouse

_PRODUCT_COLUMNS = (
    "sku, name, category, uom, pack_size, unit_cost_cents, list_price_cents, "
    "reorder_point, reorder_qty, active"
)


def _product(row: sqlite3.Row) -> Product:
    return Product(
        sku=row["sku"],
        name=row["name"],
        category=row["category"],
        uom=row["uom"],
        pack_size=int(row["pack_size"]),
        unit_cost_cents=int(row["unit_cost_cents"]),
        list_price_cents=int(row["list_price_cents"]),
        reorder_point=int(row["reorder_point"]),
        reorder_qty=int(row["reorder_qty"]),
        active=bool(row["active"]),
    )


def find(conn: sqlite3.Connection, sku: str) -> Product | None:
    row = conn.execute(
        f"SELECT {_PRODUCT_COLUMNS} FROM products WHERE sku = ?", (sku.strip().upper(),)
    ).fetchone()
    return _product(row) if row else None


def get(conn: sqlite3.Connection, sku: str) -> Product:
    product = find(conn, sku)
    if product is None:
        raise NotFound(f"unknown SKU {sku!r}")
    return product


def list_products(conn: sqlite3.Connection, *, active_only: bool = True, category: str | None = None) -> list[Product]:
    sql = f"SELECT {_PRODUCT_COLUMNS} FROM products WHERE 1 = 1"
    params: list[object] = []
    if active_only:
        sql += " AND active = 1"
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY sku"
    return [_product(r) for r in conn.execute(sql, params)]


def update_cost(conn: sqlite3.Connection, sku: str, unit_cost_cents: int) -> None:
    conn.execute("UPDATE products SET unit_cost_cents = ? WHERE sku = ?", (int(unit_cost_cents), sku))


def set_active(conn: sqlite3.Connection, sku: str, active: bool) -> None:
    cur = conn.execute("UPDATE products SET active = ? WHERE sku = ?", (1 if active else 0, sku))
    if cur.rowcount == 0:
        raise NotFound(f"unknown SKU {sku!r}")


def get_warehouse(conn: sqlite3.Connection, code: str) -> Warehouse:
    row = conn.execute(
        "SELECT code, name, region FROM warehouses WHERE code = ?", (code.strip().upper(),)
    ).fetchone()
    if row is None:
        raise NotFound(f"unknown warehouse {code!r}")
    return Warehouse(code=row["code"], name=row["name"], region=row["region"])


def list_warehouses(conn: sqlite3.Connection) -> list[Warehouse]:
    return [
        Warehouse(code=r["code"], name=r["name"], region=r["region"])
        for r in conn.execute("SELECT code, name, region FROM warehouses ORDER BY code")
    ]
