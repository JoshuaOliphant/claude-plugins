"""Read invoices from the line-level CSV export of the billing system.

Each row is one invoice line; rows sharing an ``invoice_id`` belong to the
same invoice and must agree on customer, date and currency.
"""

from __future__ import annotations

import csv
import logging
from decimal import Decimal
from pathlib import Path
from typing import Iterator, Mapping

from .. import tax
from ..models import Customer, Invoice, LineItem
from ..money import Money, parse_amount
from ..utils.dates import parse_date

log = logging.getLogger(__name__)

# Some exports carry full statements of work in the description column.
csv.field_size_limit(max(csv.field_size_limit(), 1 << 20))

REQUIRED_COLUMNS = (
    "invoice_id",
    "customer_id",
    "issue_date",
    "currency",
    "sku",
    "description",
    "quantity",
    "unit_price",
)


class SourceError(ValueError):
    def __init__(self, path, line: int, message: str):
        super().__init__(f"{path}:{line}: {message}")
        self.line = line


def read_rows(path) -> Iterator[tuple[int, dict[str, str]]]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or ())]
        if missing:
            raise SourceError(path, 1, f"missing columns: {', '.join(missing)}")
        for row in reader:
            if not any((value or "").strip() for value in row.values()):
                continue
            yield reader.line_num, {k: (v or "").strip() for k, v in row.items()}


def load_invoices(path, customers: Mapping[str, Customer], settings) -> list[Invoice]:
    invoices: dict[str, Invoice] = {}
    for line_no, row in read_rows(path):
        invoice_id = row["invoice_id"]
        customer = customers.get(row["customer_id"])
        if customer is None:
            raise SourceError(path, line_no, f"unknown customer {row['customer_id']!r}")
        currency = row["currency"].upper() or customer.currency
        invoice = invoices.get(invoice_id)
        if invoice is None:
            invoice = Invoice(
                invoice_id=invoice_id,
                customer_id=customer.customer_id,
                issue_date=parse_date(row["issue_date"]),
                currency=currency,
                tax_rate=tax.rate_for(customer.region, settings.tax_rates, settings.default_region),
                status=row.get("status") or "issued",
            )
            invoices[invoice_id] = invoice
        elif invoice.customer_id != customer.customer_id or invoice.currency != currency:
            raise SourceError(path, line_no, f"{invoice_id}: rows disagree on customer/currency")
        try:
            quantity = Decimal(row["quantity"])
            price = Money(parse_amount(row["unit_price"]), currency)
        except (ArithmeticError, ValueError) as exc:
            raise SourceError(path, line_no, str(exc)) from None
        invoice.add_line(LineItem(row["sku"], row["description"], quantity, price))
    log.info("loaded %d invoices from %s", len(invoices), path)
    return list(invoices.values())
