"""Building blocks of the summary report, one function per section."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from ..analytics import forecast, trends
from ..money import Money
from ..services import ledger
from .formatting import format_money, format_number, format_pct, key_values, render_table, truncate


@dataclass
class Section:
    title: str
    lines: list[str] = field(default_factory=list)

    def render(self) -> list[str]:
        return [self.title, "-" * len(self.title), *self.lines, ""]


def totals_section(count: int, grand: Money, average: Money, collected: Money | None,
                   outstanding: Money | None) -> Section:
    pairs = [
        ("Invoices", str(count)),
        ("Grand total", format_money(grand)),
        ("Average invoice", format_money(average)),
    ]
    if collected is not None and outstanding is not None:
        pairs.append(("Collected", format_money(collected)))
        pairs.append(("Outstanding", format_money(outstanding)))
    return Section("Totals", key_values(pairs))


def customer_section(by_customer: Mapping[str, Money], grand: Money, names: Mapping[str, str],
                     limit: int) -> Section:
    rows = []
    for customer_id, amount in ledger.top_customers(by_customer, limit):
        rows.append([
            truncate(names.get(customer_id, customer_id), 28),
            format_money(amount),
            format_pct(ledger.share_of(amount, grand), signed=False),
        ])
    others = len(by_customer) - len(rows)
    lines = render_table(["Customer", "Billed", "Share"], rows, "lrr")
    if others > 0:
        lines.append(f"(+{others} more customers)")
    return Section(f"Top {limit} customers", lines)


def trend_section(series: Sequence[trends.MonthPoint]) -> Section:
    rows = [[p.month, format_money(p.revenue), format_pct(p.growth_pct)] for p in series]
    lines = render_table(["Month", "Revenue", "Growth"], rows, "lrr")
    extremes = trends.best_and_worst(series)
    if extremes:
        best, worst = extremes
        lines.append("")
        lines.extend(key_values([
            ("Best month", f"{best.month} ({format_money(best.revenue)})"),
            ("Weakest month", f"{worst.month} ({format_money(worst.revenue)})"),
            ("Avg monthly growth", format_pct(trends.average_growth(series))),
            ("Growth streak", f"{trends.streak(series)} months"),
        ]))
    return Section("Monthly revenue", lines)


def forecast_section(series: Sequence[trends.MonthPoint], window: int, currency: str) -> Section:
    result = forecast.next_month(series, window)
    if result is None:
        return Section("Forecast", ["not enough data"])
    return Section("Forecast", key_values([
        ("Month", result.month),
        ("Expected", f"{format_number(result.expected)} {currency}"),
        ("Range", f"{format_number(result.low)} - {format_number(result.high)} {currency}"),
        ("Based on", f"last {result.window} months"),
    ]))


def aging_section(buckets: Mapping[str, Money]) -> Section:
    rows = [[label, format_money(amount)] for label, amount in buckets.items()]
    return Section("Receivables aging", render_table(["Bucket", "Outstanding"], rows, "lr"))
