"""Ledger arithmetic: totals across invoices in the reporting currency."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Iterable

from ..adapters.fx import RateTable
from ..models import Invoice
from ..money import Money
from ..utils.dates import month_key


def billable(invoices: Iterable[Invoice]) -> list[Invoice]:
    return [inv for inv in invoices if not inv.is_void]


def base_total(invoice: Invoice, fx: RateTable) -> Money:
    """Invoice total converted at the rate for its issue month."""
    return fx.convert_on(invoice.total(), invoice.issue_date)


def grand_total(invoices: Iterable[Invoice], fx: RateTable) -> Money:
    result = Money.zero(fx.base)
    for invoice in billable(invoices):
        result = result + base_total(invoice, fx)
    return result


def totals_by_customer(invoices: Iterable[Invoice], fx: RateTable) -> dict[str, Money]:
    totals: dict[str, Money] = defaultdict(lambda: Money.zero(fx.base))
    for invoice in billable(invoices):
        totals[invoice.customer_id] = totals[invoice.customer_id] + base_total(invoice, fx)
    return dict(totals)


def totals_by_month(invoices: Iterable[Invoice], fx: RateTable) -> dict[str, Money]:
    totals: dict[str, Money] = {}
    for invoice in billable(invoices):
        key = month_key(invoice.issue_date)
        totals[key] = totals.get(key, Money.zero(fx.base)) + base_total(invoice, fx)
    return dict(sorted(totals.items()))


def top_customers(by_customer: dict[str, Money], limit: int) -> list[tuple[str, Money]]:
    ranked = sorted(by_customer.items(), key=lambda item: (-item[1].amount, item[0]))
    return ranked[:limit]


def average_invoice(invoices: Iterable[Invoice], fx: RateTable) -> Money:
    items = billable(invoices)
    if not items:
        return Money.zero(fx.base)
    total = grand_total(items, fx)
    return Money(total.amount / Decimal(len(items)), total.currency).rounded()


def share_of(part: Money, whole: Money) -> Decimal:
    """Percentage of ``whole`` represented by ``part``, to one decimal place."""
    if whole.is_zero():
        return Decimal("0.0")
    return (part.amount * 100 / whole.amount).quantize(Decimal("0.1"))
