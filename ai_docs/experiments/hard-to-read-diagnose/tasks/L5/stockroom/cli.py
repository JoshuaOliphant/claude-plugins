"""Command-line interface: ``python -m stockroom <command> ...``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stockroom import __version__
from stockroom.adapters import csv_receipts, exporters
from stockroom.config import get_settings, override
from stockroom.db.connection import open_default
from stockroom.domain import units
from stockroom.domain.errors import StockroomError, ValidationError
from stockroom.repo import customers as customer_repo
from stockroom.services.catalog import Catalog
from stockroom.services.inventory import InventoryService
from stockroom.services.orders import OrderService
from stockroom.services.reports import ReportService
from stockroom.utils.formatting import render_table
from stockroom.utils.money import format_cents, parse_money


def _line_spec(text: str) -> tuple[str, int]:
    sku, sep, qty = text.partition(":")
    if not sep or not qty.strip().isdigit():
        raise argparse.ArgumentTypeError(f"expected SKU:QTY, got {text!r}")
    return sku.strip().upper(), int(qty)


def _money(text: str) -> int:
    try:
        return parse_money(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stockroom", description="Inventory and order desk")
    p.add_argument("--db", type=Path, help="database file (default from settings / STOCKROOM_DB)")
    p.add_argument("--version", action="version", version=f"stockroom {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("receive", help="post a goods receipt")
    r.add_argument("sku")
    r.add_argument("qty", type=int)
    r.add_argument("--warehouse", "-w")
    r.add_argument("--uom", help="EA, DZ or CS (default: product's unit)")
    r.add_argument("--unit-cost", type=_money, help="cost per UOM, e.g. 12.50")
    r.add_argument("--ref", help="supplier document reference")

    i = sub.add_parser("import-receipts", help="post receipts from a CSV file")
    i.add_argument("path", type=Path)

    c = sub.add_parser("count", help="record a cycle count")
    c.add_argument("sku")
    c.add_argument("counted", type=int)
    c.add_argument("--warehouse", "-w")
    c.add_argument("--ref")

    t = sub.add_parser("transfer", help="move unreserved stock between warehouses")
    t.add_argument("sku")
    t.add_argument("qty", type=int)
    t.add_argument("--from", dest="source", required=True)
    t.add_argument("--to", dest="destination", required=True)
    t.add_argument("--ref")

    o = sub.add_parser("order", help="sales orders")
    osub = o.add_subparsers(dest="order_command", required=True)
    op = osub.add_parser("place")
    op.add_argument("--customer", "-c", required=True)
    op.add_argument("--warehouse", "-w")
    op.add_argument("--line", "-l", type=_line_spec, action="append", required=True, help="SKU:QTY")
    for name in ("ship", "cancel", "show"):
        x = osub.add_parser(name)
        x.add_argument("number")

    s = sub.add_parser("stock", help="stock levels for one SKU")
    s.add_argument("sku")

    sub.add_parser("products", help="list active products")
    sub.add_parser("customers", help="list customers")

    rep = sub.add_parser("report", help="run a report")
    rsub = rep.add_subparsers(dest="report", required=True)
    for name in ("availability", "valuation", "reorder", "open-orders", "moves"):
        x = rsub.add_parser(name)
        x.add_argument("--format", "-f", choices=exporters.FORMATS, default="table")
        x.add_argument("--output", "-o", type=Path)
        if name in ("availability", "open-orders", "moves"):
            x.add_argument("--sku")
        if name != "reorder":
            x.add_argument("--warehouse", "-w")
        if name == "availability":
            x.add_argument("--all", action="store_true", help="include rows with no stock")
        if name == "moves":
            x.add_argument("--days", type=int)
    return p


def _report(args, reports: ReportService):
    if args.report == "availability":
        return reports.availability(sku=args.sku, warehouse=args.warehouse, include_empty=args.all)
    if args.report == "valuation":
        return reports.valuation(warehouse=args.warehouse)
    if args.report == "reorder":
        return reports.reorder()
    if args.report == "open-orders":
        return reports.open_orders(warehouse=args.warehouse, sku=args.sku)
    return reports.moves(sku=args.sku, warehouse=args.warehouse, days=args.days)


def _print_order(order, currency: str) -> None:
    print(f"{order.number}  {order.customer}  {order.warehouse}  {order.status}  {order.order_date}")
    rows = [
        [l.line_no, l.sku, l.qty, l.shipped_qty, l.remaining, l.status, format_cents(l.price_cents, currency)]
        for l in order.lines
    ]
    print(render_table(["Line", "SKU", "Qty", "Shipped", "Remaining", "Status", "Price"], rows))
    print(f"total: {format_cents(order.total_cents, currency)}")


def run(args) -> int:
    settings = override(db_path=args.db) if args.db else get_settings()
    conn = open_default(settings)
    try:
        catalog = Catalog(conn)
        inventory = InventoryService(conn, settings, catalog)
        orders = OrderService(conn, settings, catalog)
        reports = ReportService(conn, settings, catalog)

        if args.command == "receive":
            level = inventory.receive(
                args.sku, args.qty, warehouse=args.warehouse, uom=args.uom,
                unit_cost_cents=args.unit_cost, reference=args.ref,
            )
            print(f"received {args.qty} {args.uom or ''}".rstrip()
                  + f" {level.sku} at {level.warehouse}; on hand {level.on_hand}")
        elif args.command == "import-receipts":
            summary = csv_receipts.import_file(inventory, args.path)
            print(f"imported {summary.lines} receipt line(s), {summary.units} unit(s), {len(summary.skus)} SKU(s)")
        elif args.command == "count":
            res = inventory.count(args.sku, args.counted, warehouse=args.warehouse, reference=args.ref)
            print(f"{res.sku} at {res.warehouse}: {res.before} -> {res.after} (variance {res.variance:+d})")
        elif args.command == "transfer":
            out_level, in_level = inventory.transfer(
                args.sku, args.qty, source=args.source, destination=args.destination, reference=args.ref
            )
            print(f"moved {args.qty} {out_level.sku}: {out_level.warehouse} now {out_level.on_hand}, "
                  f"{in_level.warehouse} now {in_level.on_hand}")
        elif args.command == "order":
            if args.order_command == "place":
                order = orders.place(args.customer, args.line, warehouse=args.warehouse)
                print(f"placed {order.number}")
                _print_order(order, settings.currency)
            elif args.order_command == "ship":
                result = orders.ship(args.number)
                print(f"shipped {result.units} unit(s) on {result.order.number}; status {result.order.status}")
            elif args.order_command == "cancel":
                order = orders.cancel(args.number)
                print(f"cancelled remainder of {order.number}; status {order.status}")
            else:
                _print_order(orders.get(args.number), settings.currency)
        elif args.command == "stock":
            product = catalog.product(args.sku)
            rows = [[l.warehouse, l.on_hand, l.reserved, l.available, units.describe(l.on_hand, product.pack_size)]
                    for l in inventory.levels(product.sku)]
            print(f"{product.sku}  {product.name}")
            print(render_table(["Warehouse", "On hand", "Reserved", "Available", "Packed"], rows))
        elif args.command == "products":
            rows = [[p.sku, p.name, p.category, p.uom, p.pack_size,
                     format_cents(p.unit_cost_cents, settings.currency),
                     format_cents(p.list_price_cents, settings.currency)]
                    for p in catalog.products()]
            print(render_table(["SKU", "Name", "Category", "UOM", "Pack", "Cost", "Price"], rows))
        elif args.command == "customers":
            rows = [[c.code, c.name, c.allow_backorder, format_cents(c.credit_limit_cents, settings.currency)]
                    for c in customer_repo.list_customers(conn)]
            print(render_table(["Code", "Name", "Backorders", "Credit limit"], rows))
        elif args.command == "report":
            report = _report(args, reports)
            if args.output:
                exporters.write(report, args.output, args.format if args.format != "table" else None)
                print(f"wrote {args.output}")
            else:
                print(exporters.render(report, args.format))
        else:  # pragma: no cover - argparse enforces the choices
            raise ValidationError(f"unknown command {args.command}")
    finally:
        conn.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except StockroomError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
