"""Payment matching, outstanding balances and receivables aging."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Sequence

from ..adapters.fx import RateTable
from ..models import Invoice, Payment
from ..money import Money
from ..utils.dates import days_overdue
from .ledger import base_total, billable

log = logging.getLogger(__name__)


@dataclass
class Balance:
    invoice: Invoice
    billed: Money
    paid: Money
    payments: list[Payment] = field(default_factory=list)

    @property
    def remaining(self) -> Money:
        return self.billed - self.paid

    @property
    def settled(self) -> bool:
        return not self.remaining.amount > 0


def apply_payments(
    invoices: Iterable[Invoice], payments: Iterable[Payment], fx: RateTable
) -> dict[str, Balance]:
    balances = {
        inv.invoice_id: Balance(inv, base_total(inv, fx), Money.zero(fx.base))
        for inv in billable(invoices)
    }
    for payment in payments:
        balance = balances.get(payment.invoice_id)
        if balance is None:
            log.warning("payment %s references unknown invoice %s", payment.payment_id, payment.invoice_id)
            continue
        converted = fx.convert_on(payment.amount, balance.invoice.issue_date)
        balance.paid = balance.paid + converted
        balance.payments.append(payment)
    return balances


def collected(balances: dict[str, Balance], currency: str) -> Money:
    result = Money.zero(currency)
    for balance in balances.values():
        result = result + balance.paid
    return result


def outstanding(balances: dict[str, Balance], currency: str) -> Money:
    result = Money.zero(currency)
    for balance in balances.values():
        if not balance.settled:
            result = result + balance.remaining
    return result


def bucket_labels(buckets: Sequence[int]) -> list[str]:
    labels = ["current"]
    previous = 0
    for limit in buckets:
        labels.append(f"{previous + 1}-{limit} days")
        previous = limit
    labels.append(f"over {previous} days")
    return labels


def aging(
    balances: dict[str, Balance], as_of: date, due_days: int, buckets: Sequence[int], currency: str
) -> dict[str, Money]:
    labels = bucket_labels(buckets)
    result = {label: Money.zero(currency) for label in labels}
    for balance in balances.values():
        if balance.settled:
            continue
        overdue = days_overdue(balance.invoice.due_date(due_days), as_of)
        if overdue == 0:
            label = labels[0]
        else:
            label = labels[-1]
            for index, limit in enumerate(buckets):
                if overdue <= limit:
                    label = labels[index + 1]
                    break
        result[label] = result[label] + balance.remaining
    return result
