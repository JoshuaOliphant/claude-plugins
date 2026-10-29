"""``ledgerly export``: write invoice totals as JSON or CSV for other tools."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from decimal import Decimal
from pathlib import Path

from ..models import Invoice
from ..money import Money
from ..services import ledger
from ._common import add_common_args, add_source_arg, build_service, load_source, run


class _LedgerEncoder(json.JSONEncoder):
    def default(self, value):
        if isinstance(value, Money):
            return {"amount": f"{value.amount:.2f}", "currency": value.currency}
        if isinstance(value, Decimal):
            return str(value)
        return super().default(value)


def _record(service, invoice: Invoice) -> dict:
    return {
        "invoice_id": invoice.invoice_id,
        "customer_id": invoice.customer_id,
        "customer": service.customer_name(invoice.customer_id),
        "issue_date": invoice.issue_date.isoformat(),
        "status": invoice.status,
        "subtotal": invoice.subtotal(),
        "tax": invoice.tax(),
        "total": invoice.total(),
        "total_base": ledger.base_total(invoice, service.rates),
    }


def _write(text: str, out: Path | None) -> None:
    if out is None:
        sys.stdout.write(text)
    else:
        out.write_text(text, encoding="utf-8")


def cmd_json(args) -> int:
    service = build_service(args)
    invoices = load_source(service, args.source)
    payload = {
        "source": args.source.name,
        "base_currency": service.settings.base_currency,
        "grand_total": ledger.grand_total(invoices, service.rates),
        "invoices": [_record(service, inv) for inv in invoices],
    }
    _write(json.dumps(payload, cls=_LedgerEncoder, indent=2) + "\n", args.out)
    return 0


def cmd_csv(args) -> int:
    service = build_service(args)
    invoices = load_source(service, args.source)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["invoice_id", "customer_id", "issue_date", "status", "currency",
                     "subtotal", "tax", "total", "total_base"])
    for invoice in invoices:
        rec = _record(service, invoice)
        writer.writerow([
            rec["invoice_id"], rec["customer_id"], rec["issue_date"], rec["status"],
            invoice.currency, f"{rec['subtotal'].amount:.2f}", f"{rec['tax'].amount:.2f}",
            f"{rec['total'].amount:.2f}", f"{rec['total_base'].amount:.2f}",
        ])
    _write(buffer.getvalue(), args.out)
    return 0


def main(argv) -> int:
    parser = argparse.ArgumentParser(prog="ledgerly export")
    sub = parser.add_subparsers(dest="action", required=True)
    for name, handler in (("json", cmd_json), ("csv", cmd_csv)):
        p = sub.add_parser(name, help=f"export invoice totals as {name.upper()}")
        add_source_arg(p)
        add_common_args(p)
        p.add_argument("--out", type=Path, help="output file (default: stdout)")
        p.set_defaults(handler=handler)
    args = parser.parse_args(argv)
    return run(args.handler, args)
