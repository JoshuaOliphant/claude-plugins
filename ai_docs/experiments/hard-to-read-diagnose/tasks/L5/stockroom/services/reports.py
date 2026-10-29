"""Report builders.

Every builder returns a :class:`Report`: a title, column headers, rows of
plain values and optional footer totals. Rendering (table / CSV / JSON)
is done by ``adapters.exporters`` so the same report can feed the
terminal, a spreadsheet or another script.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from stockroom.config import Settings
from stockroom.repo import moves as move_repo
from stockroom.repo import orders as order_repo
from stockroom.repo import stock as stock_repo
from stockroom.services.catalog import Catalog
from stockroom.utils import dates
from stockroom.utils.money import extend, format_cents


@dataclass
class Report:
    name: str
    title: str
    columns: list[str]
    rows: list[list[Any]] = field(default_factory=list)
    totals: dict[str, Any] = field(default_factory=dict)
    as_of: date | None = None


class ReportService:
    def __init__(self, conn: sqlite3.Connection, settings: Settings, catalog: Catalog | None = None):
        self.conn = conn
        self.settings = settings
        self.catalog = catalog or Catalog(conn)

    # -- availability ---------------------------------------------------

    def availability(
        self,
        *,
        sku: str | None = None,
        warehouse: str | None = None,
        include_empty: bool = False,
    ) -> Report:
        """On hand, promised and free stock per SKU and warehouse."""
        sku = sku.strip().upper() if sku else None
        wh = self.catalog.warehouse(warehouse).code if warehouse else None
        if sku:
            self.catalog.product(sku)
        report = Report(
            name="availability",
            title="Stock availability",
            columns=["SKU", "Name", "Warehouse", "On hand", "Reserved", "Available", "Backordered"],
            as_of=dates.today(),
        )
        total_available = total_backordered = 0
        for row in stock_repo.list_availability(self.conn, sku=sku, warehouse=wh):
            if not include_empty and not sku and row.on_hand == 0 and row.reserved == 0:
                continue
            report.rows.append(
                [row.sku, row.name, row.warehouse, row.on_hand, row.reserved, row.available, row.backordered]
            )
            total_available += row.available
            total_backordered += row.backordered
        report.totals = {"available": total_available, "backordered": total_backordered}
        return report

    # -- valuation ------------------------------------------------------

    def valuation(self, *, warehouse: str | None = None) -> Report:
        """Inventory value at moving-average cost."""
        wh = self.catalog.warehouse(warehouse).code if warehouse else None
        report = Report(
            name="valuation",
            title="Inventory valuation",
            columns=["SKU", "Name", "Warehouse", "On hand", "Unit cost", "Value"],
            as_of=dates.today(),
        )
        total = 0
        for row in stock_repo.list_availability(self.conn, warehouse=wh):
            if row.on_hand <= 0:
                continue
            product = self.catalog.product(row.sku)
            value = extend(row.on_hand, product.unit_cost_cents)
            total += value
            report.rows.append(
                [
                    row.sku,
                    row.name,
                    row.warehouse,
                    row.on_hand,
                    format_cents(product.unit_cost_cents, self.settings.currency),
                    format_cents(value, self.settings.currency),
                ]
            )
        report.totals = {"value": format_cents(total, self.settings.currency), "value_cents": total}
        return report

    # -- reorder --------------------------------------------------------

    def reorder(self) -> Report:
        """SKUs whose network-wide free stock is at or below the reorder point."""
        free_by_sku: dict[str, int] = defaultdict(int)
        meta: dict[str, tuple[str, int, int]] = {}
        for row in stock_repo.list_availability(self.conn):
            free_by_sku[row.sku] += row.on_hand - row.reserved
            meta[row.sku] = (row.name, row.reorder_point, row.reorder_qty)

        report = Report(
            name="reorder",
            title="Reorder suggestions",
            columns=["SKU", "Name", "Free", "Reorder point", "Suggested qty"],
            as_of=dates.today(),
        )
        for sku in sorted(free_by_sku):
            name, point, lot = meta[sku]
            free = free_by_sku[sku]
            if point <= 0 or free > point:
                continue
            shortfall = point - free
            lots = max(1, -(-shortfall // lot)) if lot > 0 else 1
            suggested = lots * lot if lot > 0 else shortfall
            report.rows.append([sku, name, free, point, suggested])
        report.totals = {"skus": len(report.rows)}
        return report

    # -- open orders ----------------------------------------------------

    def open_orders(self, *, warehouse: str | None = None, sku: str | None = None) -> Report:
        wh = self.catalog.warehouse(warehouse).code if warehouse else None
        report = Report(
            name="open-orders",
            title="Open order lines",
            columns=["Order", "Date", "Customer", "Warehouse", "Line", "SKU", "Ordered", "Shipped", "Remaining", "Age"],
            as_of=dates.today(),
        )
        remaining_total = 0
        for order, line in order_repo.open_lines(self.conn, warehouse=wh, sku=sku.upper() if sku else None):
            report.rows.append(
                [
                    order.number,
                    order.order_date.isoformat(),
                    order.customer,
                    order.warehouse,
                    line.line_no,
                    line.sku,
                    line.qty,
                    line.shipped_qty,
                    line.remaining,
                    dates.age_in_days(order.order_date),
                ]
            )
            remaining_total += line.remaining
        report.totals = {"remaining": remaining_total}
        return report

    # -- movement journal -----------------------------------------------

    def moves(self, *, sku: str | None = None, warehouse: str | None = None, days: int | None = None) -> Report:
        days = self.settings.moves_window_days if days is None else days
        since = dates.window_start(days)
        wh = self.catalog.warehouse(warehouse).code if warehouse else None
        report = Report(
            name="moves",
            title=f"Stock moves since {since.isoformat()}",
            columns=["Date", "SKU", "Warehouse", "Kind", "Qty", "Reference"],
            as_of=dates.today(),
        )
        net: dict[str, int] = defaultdict(int)
        for move in move_repo.list_moves(self.conn, sku=sku.upper() if sku else None, warehouse=wh, since=since):
            report.rows.append(
                [move.moved_on.isoformat(), move.sku, move.warehouse, move.kind, move.qty, move.reference or ""]
            )
            net[move.kind] += move.qty
        report.totals = dict(sorted(net.items()))
        return report


REPORTS = ("availability", "valuation", "reorder", "open-orders", "moves")
