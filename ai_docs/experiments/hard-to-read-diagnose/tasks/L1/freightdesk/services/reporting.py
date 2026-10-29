"""Manifest summaries for the shipping desk's end-of-day report."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from freightdesk.domain.money import Money
from freightdesk.domain.quote import Quote
from freightdesk.pricing.engine import billable_total
from freightdesk.utils.decimals import plain


@dataclass
class CarrierSummary:
    carrier: str
    currency: str
    shipments: int = 0
    parcels: int = 0
    billable_kg: Decimal = Decimal(0)
    total: Money | None = None
    surcharges: dict[str, int] = field(default_factory=dict)

    def add(self, quote: Quote) -> None:
        self.shipments += 1
        self.parcels += len(quote.parcels)
        self.billable_kg += billable_total(quote)
        self.total = quote.total if self.total is None else self.total + quote.total
        for line in quote.lines:
            if line.code.startswith("SUR-"):
                self.surcharges[line.code] = self.surcharges.get(line.code, 0) + 1


def summarise(quotes: list[Quote]) -> list[CarrierSummary]:
    by_carrier: dict[tuple[str, str], CarrierSummary] = {}
    for quote in quotes:
        key = (quote.carrier, quote.currency)
        if key not in by_carrier:
            by_carrier[key] = CarrierSummary(quote.carrier, quote.currency)
        by_carrier[key].add(quote)
    return [by_carrier[k] for k in sorted(by_carrier)]


def zone_histogram(quotes: list[Quote]) -> dict[str, dict[str, int]]:
    hist: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for quote in quotes:
        hist[quote.carrier][quote.zone] += 1
    return {c: dict(sorted(z.items())) for c, z in sorted(hist.items())}


def format_summary(summaries: list[CarrierSummary], failures: list[tuple[str, str]]) -> str:
    lines = ["carrier     shipments parcels  billable_kg        total"]
    for s in summaries:
        total = f"{s.total.amount:.2f} {s.currency}" if s.total else "-"
        lines.append(
            f"{s.carrier:<11} {s.shipments:>9} {s.parcels:>7} {plain(s.billable_kg):>12} {total:>16}"
        )
        if s.surcharges:
            parts = ", ".join(f"{code}x{n}" for code, n in sorted(s.surcharges.items()))
            lines.append(f"{'':<11} surcharges: {parts}")
    if failures:
        lines.append("")
        lines.append(f"{len(failures)} shipment(s) could not be rated:")
        for ref, reason in failures:
            lines.append(f"  {ref}: {reason}")
    return "\n".join(lines)
