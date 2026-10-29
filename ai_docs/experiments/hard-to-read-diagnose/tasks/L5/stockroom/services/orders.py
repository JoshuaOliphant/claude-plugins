"""Order desk: placing, shipping and cancelling sales orders.

Placing an order reserves stock at the order's warehouse. Customers flagged
``allow_backorder`` may reserve more than is on hand; their lines ship as
stock arrives. Everyone else is refused when a line cannot be covered from
unreserved stock.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date

from stockroom.config import Settings
from stockroom.db.transaction import transaction
from stockroom.domain.errors import InsufficientStock, InvalidState, ValidationError
from stockroom.domain.models import Order, OrderLine
from stockroom.repo import customers as customer_repo
from stockroom.repo import moves as move_repo
from stockroom.repo import orders as order_repo
from stockroom.repo import stock as stock_repo
from stockroom.services.catalog import Catalog
from stockroom.utils import dates


@dataclass
class ShipmentResult:
    order: Order
    shipped: dict[str, int] = field(default_factory=dict)

    @property
    def units(self) -> int:
        return sum(self.shipped.values())


def merge_lines(lines: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """Combine repeated SKUs while keeping first-seen order."""
    merged: dict[str, int] = {}
    for sku, qty in lines:
        key = sku.strip().upper()
        if qty <= 0:
            raise ValidationError(f"quantity for {key} must be positive")
        merged[key] = merged.get(key, 0) + int(qty)
    return list(merged.items())


class OrderService:
    def __init__(self, conn: sqlite3.Connection, settings: Settings, catalog: Catalog | None = None):
        self.conn = conn
        self.settings = settings
        self.catalog = catalog or Catalog(conn)

    def place(
        self,
        customer_code: str,
        lines: list[tuple[str, int]],
        *,
        warehouse: str | None = None,
        order_date: date | None = None,
    ) -> Order:
        if not lines:
            raise ValidationError("an order needs at least one line")
        customer = customer_repo.get(self.conn, customer_code)
        wh = self.catalog.warehouse(warehouse or self.settings.default_warehouse).code
        merged = merge_lines(lines)
        products = [self.catalog.product(sku) for sku, _ in merged]

        with transaction(self.conn):
            if not customer.allow_backorder:
                for (sku, qty), product in zip(merged, products):
                    level = stock_repo.get_level(self.conn, product.sku, wh)
                    if level.available < qty:
                        raise InsufficientStock(product.sku, wh, qty, level.available)

            order_total = sum(qty * p.list_price_cents for (_, qty), p in zip(merged, products))
            if customer.credit_limit_cents:
                exposure = customer_repo.open_balance_cents(self.conn, customer.code) + order_total
                if exposure > customer.credit_limit_cents:
                    raise ValidationError(
                        f"order would put {customer.code} over its credit limit"
                    )

            number = order_repo.next_number(self.conn)
            order_repo.insert_order(self.conn, number, customer.code, wh, order_date or dates.today())
            for line_no, ((_, qty), product) in enumerate(zip(merged, products), start=1):
                order_repo.insert_line(
                    self.conn,
                    OrderLine(
                        id=None,
                        order_number=number,
                        line_no=line_no,
                        sku=product.sku,
                        qty=qty,
                        shipped_qty=0,
                        price_cents=product.list_price_cents,
                    ),
                )
                stock_repo.apply_delta(self.conn, product.sku, wh, reserved=qty)
        return order_repo.get(self.conn, number)

    def ship(self, number: str) -> ShipmentResult:
        """Ship whatever can be shipped now; the rest stays open."""
        order = order_repo.get(self.conn, number)
        if order.status not in ("open", "partial"):
            raise InvalidState(f"order {order.number} is {order.status}")

        result = ShipmentResult(order=order)
        with transaction(self.conn):
            for line in order.open_lines:
                level = stock_repo.get_level(self.conn, line.sku, order.warehouse)
                qty = min(line.remaining, max(level.on_hand, 0))
                if qty <= 0:
                    continue
                stock_repo.apply_delta(self.conn, line.sku, order.warehouse, on_hand=-qty, reserved=-qty)
                order_repo.add_shipped(self.conn, line.id, qty)
                move_repo.record(
                    self.conn,
                    sku=line.sku,
                    warehouse=order.warehouse,
                    kind="ship",
                    qty=-qty,
                    reference=order.number,
                    moved_on=dates.today(),
                )
                result.shipped[line.sku] = result.shipped.get(line.sku, 0) + qty

            refreshed = order_repo.get(self.conn, order.number)
            status = refreshed.derive_status()
            if status != refreshed.status:
                order_repo.set_status(self.conn, order.number, status)
        result.order = order_repo.get(self.conn, order.number)
        return result

    def cancel(self, number: str) -> Order:
        """Cancel the unshipped remainder of an order and release its reservations."""
        order = order_repo.get(self.conn, number)
        if order.status in ("shipped", "cancelled"):
            raise InvalidState(f"order {order.number} is already {order.status}")
        with transaction(self.conn):
            for line in order.open_lines:
                stock_repo.apply_delta(self.conn, line.sku, order.warehouse, reserved=-line.remaining)
                order_repo.set_line_status(self.conn, line.id, "cancelled")
            refreshed = order_repo.get(self.conn, order.number)
            shipped_any = any(l.shipped_qty > 0 for l in refreshed.lines)
            order_repo.set_status(self.conn, order.number, "shipped" if shipped_any else "cancelled")
        return order_repo.get(self.conn, order.number)

    def get(self, number: str) -> Order:
        return order_repo.get(self.conn, number)
