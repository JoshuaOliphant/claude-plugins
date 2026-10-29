"""Receiving, cycle counts and inter-warehouse transfers."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from stockroom.config import Settings
from stockroom.db.transaction import transaction
from stockroom.domain import units
from stockroom.domain.errors import InsufficientStock, ValidationError
from stockroom.domain.models import StockLevel
from stockroom.repo import moves as move_repo
from stockroom.repo import products as product_repo
from stockroom.repo import stock as stock_repo
from stockroom.services.catalog import Catalog
from stockroom.utils import dates
from stockroom.utils.money import weighted_average_cents


@dataclass(frozen=True)
class CountResult:
    sku: str
    warehouse: str
    before: int
    after: int

    @property
    def variance(self) -> int:
        return self.after - self.before


class InventoryService:
    def __init__(self, conn: sqlite3.Connection, settings: Settings, catalog: Catalog | None = None):
        self.conn = conn
        self.settings = settings
        self.catalog = catalog or Catalog(conn)

    def _warehouse(self, code: str | None) -> str:
        return self.catalog.warehouse(code or self.settings.default_warehouse).code

    def _check_not_negative(self, level: StockLevel) -> None:
        if level.on_hand < 0 and not self.settings.allow_negative_on_hand:
            raise InsufficientStock(level.sku, level.warehouse, -level.on_hand, 0)

    def receive(
        self,
        sku: str,
        qty: int,
        *,
        warehouse: str | None = None,
        uom: str | None = None,
        unit_cost_cents: int | None = None,
        reference: str | None = None,
        received_on: date | None = None,
    ) -> StockLevel:
        product = self.catalog.product(sku)
        wh = self._warehouse(warehouse)
        uom = units.normalize_uom(uom or product.uom)
        qty_each = units.to_each(qty, uom, product.pack_size)
        if qty_each <= 0:
            raise ValidationError(f"receipt quantity must be positive, got {qty} {uom}")

        if unit_cost_cents is None:
            cost_each = product.unit_cost_cents
        else:
            cost_each = units.per_each_cost(unit_cost_cents, uom, product.pack_size)

        with transaction(self.conn):
            stock_before = stock_repo.total_on_hand(self.conn, product.sku)
            current = product_repo.get(self.conn, product.sku)
            new_cost = weighted_average_cents(stock_before, current.unit_cost_cents, qty_each, cost_each)
            level = stock_repo.apply_delta(self.conn, product.sku, wh, on_hand=qty_each)
            product_repo.update_cost(self.conn, product.sku, new_cost)
            move_repo.record(
                self.conn,
                sku=product.sku,
                warehouse=wh,
                kind="receipt",
                qty=qty_each,
                reference=reference,
                unit_cost_cents=cost_each,
                moved_on=received_on or dates.today(),
            )
        self.catalog.invalidate(product.sku)
        return level

    def count(
        self,
        sku: str,
        counted: int,
        *,
        warehouse: str | None = None,
        reference: str | None = None,
    ) -> CountResult:
        """Record a cycle count: set on-hand to what was physically counted."""
        if counted < 0:
            raise ValidationError("counted quantity cannot be negative")
        product = self.catalog.product(sku)
        wh = self._warehouse(warehouse)
        with transaction(self.conn):
            before = stock_repo.get_level(self.conn, product.sku, wh)
            delta = int(counted) - before.on_hand
            if delta:
                stock_repo.apply_delta(self.conn, product.sku, wh, on_hand=delta)
                move_repo.record(
                    self.conn,
                    sku=product.sku,
                    warehouse=wh,
                    kind="adjust",
                    qty=delta,
                    reference=reference or "cycle count",
                    moved_on=dates.today(),
                )
        return CountResult(product.sku, wh, before.on_hand, int(counted))

    def transfer(
        self,
        sku: str,
        qty: int,
        *,
        source: str,
        destination: str,
        reference: str | None = None,
    ) -> tuple[StockLevel, StockLevel]:
        product = self.catalog.product(sku)
        src = self._warehouse(source)
        dst = self._warehouse(destination)
        if src == dst:
            raise ValidationError("source and destination warehouse are the same")
        if qty <= 0:
            raise ValidationError("transfer quantity must be positive")

        with transaction(self.conn):
            level = stock_repo.get_level(self.conn, product.sku, src)
            # Reserved stock stays put; only unpromised units can move.
            if level.available < qty:
                raise InsufficientStock(product.sku, src, qty, level.available)
            out_level = stock_repo.apply_delta(self.conn, product.sku, src, on_hand=-qty)
            in_level = stock_repo.apply_delta(self.conn, product.sku, dst, on_hand=qty)
            ref = reference or f"{src}->{dst}"
            today = dates.today()
            move_repo.record(self.conn, sku=product.sku, warehouse=src, kind="transfer_out",
                             qty=-qty, reference=ref, moved_on=today)
            move_repo.record(self.conn, sku=product.sku, warehouse=dst, kind="transfer_in",
                             qty=qty, reference=ref, moved_on=today)
        return out_level, in_level

    def levels(self, sku: str) -> list[StockLevel]:
        product = self.catalog.product(sku)
        return stock_repo.levels_for_sku(self.conn, product.sku)

