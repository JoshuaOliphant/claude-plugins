"""Read-mostly access to products and warehouses with a small in-process cache.

Batch jobs (CSV imports, report runs) look the same product up hundreds of
times; caching avoids a round trip per line. Anything that changes a
product must call :meth:`Catalog.invalidate`.
"""

from __future__ import annotations

import sqlite3

from stockroom.domain.models import Product, Warehouse
from stockroom.repo import products as product_repo


class Catalog:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._products: dict[str, Product] = {}
        self._warehouses: dict[str, Warehouse] | None = None

    def product(self, sku: str) -> Product:
        key = sku.strip().upper()
        cached = self._products.get(key)
        if cached is None:
            cached = product_repo.get(self._conn, key)
            self._products[key] = cached
        return cached

    def products(self, *, category: str | None = None) -> list[Product]:
        items = product_repo.list_products(self._conn, category=category)
        for p in items:
            self._products[p.sku] = p
        return items

    def warehouse(self, code: str) -> Warehouse:
        if self._warehouses is None:
            self._warehouses = {w.code: w for w in product_repo.list_warehouses(self._conn)}
        key = code.strip().upper()
        if key not in self._warehouses:
            # Fall through to the repository so the error message is uniform.
            return product_repo.get_warehouse(self._conn, key)
        return self._warehouses[key]

    def warehouses(self) -> list[Warehouse]:
        self.warehouse_codes()
        return list(self._warehouses.values())

    def warehouse_codes(self) -> list[str]:
        if self._warehouses is None:
            self._warehouses = {w.code: w for w in product_repo.list_warehouses(self._conn)}
        return sorted(self._warehouses)

    def invalidate(self, sku: str | None = None) -> None:
        if sku is None:
            self._products.clear()
        else:
            self._products.pop(sku.strip().upper(), None)
