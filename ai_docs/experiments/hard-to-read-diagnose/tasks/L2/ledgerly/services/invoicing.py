"""Invoice loading and lookup, wired to settings and reference data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .. import tax
from ..adapters import csv_source, fx, json_source
from ..config import Settings
from ..models import Customer, Invoice
from ..money import Money


class InvoiceNotFound(LookupError):
    pass


@dataclass
class InvoiceService:
    settings: Settings
    customers: Mapping[str, Customer]
    rates: fx.RateTable

    @classmethod
    def from_settings(cls, settings: Settings, customers_file=None, fx_file=None) -> "InvoiceService":
        customers = json_source.load_customers(customers_file or settings.customers_file)
        fx_path = Path(fx_file or settings.fx_rates_file)
        rates = fx.load_rates(fx_path) if fx_path.exists() else fx.identity_table(settings.base_currency)
        if rates.base != settings.base_currency:
            raise ValueError(f"FX table base {rates.base} != {settings.base_currency}")
        return cls(settings, customers, rates)

    def load(self, path) -> list[Invoice]:
        return csv_source.load_invoices(path, self.customers, self.settings)

    def find(self, invoices: list[Invoice], invoice_id: str) -> Invoice:
        for invoice in invoices:
            if invoice.invoice_id == invoice_id:
                return invoice
        raise InvoiceNotFound(invoice_id)

    def customer_name(self, customer_id: str) -> str:
        customer = self.customers.get(customer_id)
        return customer.name if customer else customer_id

    def validate(self, invoice: Invoice) -> list[str]:
        problems = []
        if not invoice.lines:
            problems.append("no lines")
        for line in invoice.lines:
            if line.quantity <= 0:
                problems.append(f"{line.sku}: non-positive quantity {line.quantity}")
            if line.unit_price.is_negative():
                problems.append(f"{line.sku}: negative unit price")
        customer = self.customers.get(invoice.customer_id)
        if customer is not None and not customer.active:
            problems.append(f"customer {customer.customer_id} is inactive")
        return problems

    def describe(self, invoice: Invoice) -> dict:
        subtotal = invoice.subtotal()
        tax_amount = invoice.tax()
        return {
            "invoice_id": invoice.invoice_id,
            "customer": self.customer_name(invoice.customer_id),
            "issue_date": invoice.issue_date.isoformat(),
            "due_date": invoice.due_date(self.settings.due_days).isoformat(),
            "status": invoice.status,
            "lines": [
                {
                    "sku": line.sku,
                    "description": line.description,
                    "quantity": line.quantity,
                    "unit_price": line.unit_price,
                    "amount": line.amount,
                }
                for line in invoice.lines
            ],
            "subtotal": subtotal,
            "tax": tax_amount,
            "tax_rate": tax.effective_rate(subtotal, tax_amount),
            "total": invoice.total(),
            "total_base": self.rates.convert_on(invoice.total(), invoice.issue_date),
        }

    def base_currency_zero(self) -> Money:
        return Money.zero(self.settings.base_currency)
