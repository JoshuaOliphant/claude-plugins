"""``ledgerly invoice``: totals, listings and single-invoice detail."""

from __future__ import annotations

import argparse

from ..reporting.formatting import (
    format_money,
    format_pct,
    format_quantity,
    key_values,
    render_table,
    truncate,
)
from ..services import ledger
from ._common import CommandError, add_common_args, add_source_arg, build_service, load_source, run


def cmd_total(args) -> int:
    service = build_service(args)
    invoices = load_source(service, args.source)
    rates = service.rates
    print(f"Invoices: {len(ledger.billable(invoices))}")
    print(f"Grand total: {format_money(ledger.grand_total(invoices, rates))}")
    if args.by_customer:
        by_customer = ledger.totals_by_customer(invoices, rates)
        rows = [
            [cid, truncate(service.customer_name(cid), 28), format_money(amount)]
            for cid, amount in sorted(by_customer.items())
        ]
        print()
        print("\n".join(render_table(["ID", "Customer", "Billed"], rows, "llr")))
    return 0


def cmd_list(args) -> int:
    service = build_service(args)
    invoices = load_source(service, args.source)
    if args.customer:
        invoices = [inv for inv in invoices if inv.customer_id == args.customer]
    rows = [
        [
            inv.invoice_id,
            inv.issue_date.isoformat(),
            truncate(service.customer_name(inv.customer_id), 24),
            inv.status,
            format_money(inv.total()),
        ]
        for inv in sorted(invoices, key=lambda i: (i.issue_date, i.invoice_id))
    ]
    print("\n".join(render_table(["Invoice", "Date", "Customer", "Status", "Total"], rows, "llllr")))
    return 0


def cmd_show(args) -> int:
    service = build_service(args)
    invoices = load_source(service, args.source)
    try:
        invoice = service.find(invoices, args.invoice_id)
    except LookupError:
        raise CommandError(f"invoice {args.invoice_id} not found in {args.source}") from None
    info = service.describe(invoice)
    print("\n".join(key_values([
        ("Invoice", info["invoice_id"]),
        ("Customer", info["customer"]),
        ("Issued", info["issue_date"]),
        ("Due", info["due_date"]),
        ("Status", info["status"]),
    ])))
    print()
    rows = [
        [l["sku"], truncate(l["description"], 30), format_quantity(l["quantity"]),
         format_money(l["unit_price"]), format_money(l["amount"])]
        for l in info["lines"]
    ]
    print("\n".join(render_table(["SKU", "Description", "Qty", "Unit", "Amount"], rows, "llrrr")))
    print()
    pairs = [
        ("Subtotal", format_money(info["subtotal"])),
        (f"Tax ({format_pct(info['tax_rate'] * 100, signed=False)})", format_money(info["tax"])),
        ("Total", format_money(info["total"])),
    ]
    if info["total_base"].currency != info["total"].currency:
        pairs.append(("Total (base)", format_money(info["total_base"])))
    print("\n".join(key_values(pairs)))
    problems = service.validate(invoice)
    for problem in problems:
        print(f"warning: {problem}")
    return 0


def main(argv) -> int:
    parser = argparse.ArgumentParser(prog="ledgerly invoice")
    sub = parser.add_subparsers(dest="action", required=True)

    total = sub.add_parser("total", help="grand total of an export")
    add_source_arg(total)
    add_common_args(total)
    total.add_argument("--by-customer", action="store_true")
    total.set_defaults(handler=cmd_total)

    listing = sub.add_parser("list", help="list invoices")
    add_source_arg(listing)
    add_common_args(listing)
    listing.add_argument("--customer")
    listing.set_defaults(handler=cmd_list)

    show = sub.add_parser("show", help="show one invoice")
    add_source_arg(show)
    show.add_argument("invoice_id")
    add_common_args(show)
    show.set_defaults(handler=cmd_show)

    args = parser.parse_args(argv)
    return run(args.handler, args)
