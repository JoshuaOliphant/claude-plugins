"""Domain models: customers, invoices, line items and payments."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from . import tax
from .money import Money, total


@dataclass(frozen=True)
class Customer:
    customer_id: str
    name: str
    region: str
    currency: str = "USD"
    email: str = ""
    active: bool = True

    @property
    def display_name(self) -> str:
        return f"{self.name} ({self.customer_id})"


@dataclass(frozen=True)
class LineItem:
    sku: str
    description: str
    quantity: Decimal
    unit_price: Money

    @property
    def amount(self) -> Money:
        return (self.unit_price * self.quantity).rounded()


@dataclass
class Invoice:
    invoice_id: str
    customer_id: str
    issue_date: date
    currency: str
    lines: list[LineItem] = field(default_factory=list)
    tax_rate: Decimal = Decimal("0")
    status: str = "issued"

    def add_line(self, line: LineItem) -> None:
        if line.unit_price.currency != self.currency:
            raise ValueError(
                f"{self.invoice_id}: line in {line.unit_price.currency}, invoice in {self.currency}"
            )
        self.lines.append(line)

    def subtotal(self) -> Money:
        return total((line.amount for line in self.lines), self.currency)

    def tax(self) -> Money:
        return tax.compute_tax(self.subtotal(), self.tax_rate)

    def total(self) -> Money:
        return self.subtotal() + self.tax()

    def due_date(self, due_days: int) -> date:
        return self.issue_date + timedelta(days=due_days)

    @property
    def is_void(self) -> bool:
        return self.status == "void"


@dataclass(frozen=True)
class Payment:
    payment_id: str
    invoice_id: str
    received: date
    amount: Money
    method: str = "transfer"
