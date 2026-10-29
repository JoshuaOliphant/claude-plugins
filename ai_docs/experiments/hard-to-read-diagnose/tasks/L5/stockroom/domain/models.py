"""Plain data objects.

Quantities are always integers in each-units (``EA``); money is always an
integer number of cents. Conversion from cases or decimal prices happens at
the edges (``domain.units`` and ``utils.money``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Warehouse:
    code: str
    name: str
    region: str | None = None


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    category: str | None
    uom: str
    pack_size: int
    unit_cost_cents: int
    list_price_cents: int
    reorder_point: int
    reorder_qty: int
    active: bool = True

    @property
    def margin_cents(self) -> int:
        return self.list_price_cents - self.unit_cost_cents


@dataclass(frozen=True)
class Customer:
    code: str
    name: str
    allow_backorder: bool
    credit_limit_cents: int


@dataclass(frozen=True)
class StockLevel:
    sku: str
    warehouse: str
    on_hand: int
    reserved: int
    updated_at: str | None = None

    @property
    def free(self) -> int:
        """Units not promised to anyone; negative when reservations exceed stock."""
        return self.on_hand - self.reserved

    @property
    def available(self) -> int:
        return max(self.free, 0)

    @property
    def backordered(self) -> int:
        return max(-self.free, 0)


@dataclass(frozen=True)
class AvailabilityRow:
    sku: str
    name: str
    warehouse: str
    on_hand: int
    reserved: int
    reorder_point: int
    reorder_qty: int

    @property
    def available(self) -> int:
        return max(self.on_hand - self.reserved, 0)

    @property
    def backordered(self) -> int:
        return max(self.reserved - self.on_hand, 0)


@dataclass
class OrderLine:
    id: int | None
    order_number: str
    line_no: int
    sku: str
    qty: int
    shipped_qty: int
    price_cents: int
    status: str = "open"

    @property
    def remaining(self) -> int:
        if self.status == "cancelled":
            return 0
        return max(self.qty - self.shipped_qty, 0)

    @property
    def extended_cents(self) -> int:
        return self.qty * self.price_cents


@dataclass
class Order:
    number: str
    customer: str
    warehouse: str
    status: str
    order_date: date
    lines: list[OrderLine] = field(default_factory=list)
    updated_at: str | None = None

    @property
    def total_cents(self) -> int:
        return sum(line.extended_cents for line in self.lines if line.status != "cancelled")

    @property
    def open_lines(self) -> list[OrderLine]:
        return [line for line in self.lines if line.remaining > 0]

    def derive_status(self) -> str:
        live = [line for line in self.lines if line.status != "cancelled"]
        if not live:
            return "cancelled"
        if all(line.remaining == 0 for line in live):
            return "shipped"
        if any(line.shipped_qty > 0 for line in live):
            return "partial"
        return "open"


@dataclass(frozen=True)
class StockMove:
    id: int | None
    sku: str
    warehouse: str
    kind: str
    qty: int
    reference: str | None
    unit_cost_cents: int | None
    moved_on: date
