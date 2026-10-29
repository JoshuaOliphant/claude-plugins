"""The ledger summary report."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Sequence

from ..analytics import trends
from ..models import Invoice, Payment
from ..services import ledger, payments as payment_service
from ..services.invoicing import InvoiceService
from .formatting import rule
from .sections import (
    Section,
    aging_section,
    customer_section,
    forecast_section,
    totals_section,
    trend_section,
)


@dataclass
class SummaryReport:
    source: str
    as_of: date
    sections: list[Section] = field(default_factory=list)

    def render(self) -> str:
        header = f"LEDGER SUMMARY  source={self.source}  as of {self.as_of.isoformat()}"
        lines = [header, rule("="), ""]
        for section in self.sections:
            lines.extend(section.render())
        return "\n".join(lines).rstrip() + "\n"


def build_summary(
    service: InvoiceService,
    invoices: Sequence[Invoice],
    source: Path,
    as_of: date,
    payments: Sequence[Payment] | None = None,
    include: Sequence[str] = ("totals", "customers", "trend", "forecast", "aging"),
) -> SummaryReport:
    settings = service.settings
    rates = service.rates
    base = settings.base_currency

    grand = ledger.grand_total(invoices, rates)
    average = ledger.average_invoice(invoices, rates)
    balances = None
    collected = outstanding = None
    if payments is not None:
        balances = payment_service.apply_payments(invoices, payments, rates)
        collected = payment_service.collected(balances, base)
        outstanding = payment_service.outstanding(balances, base)

    series = trends.monthly_series(ledger.totals_by_month(invoices, rates), base)
    names = {cid: c.name for cid, c in service.customers.items()}

    report = SummaryReport(source=source.name, as_of=as_of)
    for name in include:
        if name == "totals":
            count = len(ledger.billable(invoices))
            report.sections.append(totals_section(count, grand, average, collected, outstanding))
        elif name == "customers":
            by_customer = ledger.totals_by_customer(invoices, rates)
            report.sections.append(customer_section(by_customer, grand, names, settings.top_customers))
        elif name == "trend":
            report.sections.append(trend_section(series))
        elif name == "forecast":
            report.sections.append(forecast_section(series, settings.forecast_window, base))
        elif name == "aging" and balances is not None:
            buckets = payment_service.aging(
                balances, as_of, settings.due_days, settings.aging_buckets, base
            )
            report.sections.append(aging_section(buckets))
    return report
