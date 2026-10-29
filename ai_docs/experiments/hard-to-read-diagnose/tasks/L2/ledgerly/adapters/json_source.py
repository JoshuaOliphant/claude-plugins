"""JSON loaders for customer master data and payment records."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ..models import Customer, Payment
from ..money import Money, parse_amount
from ..utils.cache import file_memo
from ..utils.dates import parse_date

log = logging.getLogger(__name__)


class RecordError(ValueError):
    pass


def _read(path) -> object:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


@file_memo
def load_customers(path) -> dict[str, Customer]:
    raw = _read(path)
    records = raw["customers"] if isinstance(raw, dict) else raw
    customers: dict[str, Customer] = {}
    for record in records:
        try:
            customer = Customer(
                customer_id=record["id"],
                name=record["name"],
                region=record.get("region", "").upper(),
                currency=record.get("currency", "USD").upper(),
                email=record.get("email", ""),
                active=bool(record.get("active", True)),
            )
        except KeyError as exc:
            raise RecordError(f"customer record missing {exc.args[0]!r}: {record}") from None
        if customer.customer_id in customers:
            log.warning("duplicate customer id %s; keeping the first", customer.customer_id)
            continue
        customers[customer.customer_id] = customer
    return customers


def load_payments(path) -> list[Payment]:
    raw = _read(path)
    records = raw["payments"] if isinstance(raw, dict) else raw
    payments = []
    for record in records:
        try:
            payments.append(
                Payment(
                    payment_id=record["id"],
                    invoice_id=record["invoice"],
                    received=parse_date(record["received"]),
                    amount=Money(parse_amount(str(record["amount"])), record.get("currency", "USD")),
                    method=record.get("method", "transfer"),
                )
            )
        except KeyError as exc:
            raise RecordError(f"payment record missing {exc.args[0]!r}: {record}") from None
    payments.sort(key=lambda p: (p.received, p.payment_id))
    return payments
