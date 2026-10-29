"""Terminal summaries of a ledger."""

from __future__ import annotations

from dataclasses import dataclass

from ledgerkit.formatting.numbers import NumberLocale
from ledgerkit.formatting.templates import render
from ledgerkit.models import Ledger
from ledgerkit.money import Money, total
from ledgerkit.utils.dates import iter_months
from ledgerkit.utils.text import render_table, truncate


@dataclass
class Summary:
    count: int
    income: Money
    spending: Money
    net: Money
    by_category: dict[str, Money]
    by_month: dict[str, Money]
    period: str


def summarize(ledger: Ledger) -> Summary:
    income = total((t.amount for t in ledger if not t.is_expense), ledger.currency)
    spending = total((t.amount for t in ledger if t.is_expense), ledger.currency)
    by_month = dict(ledger.totals_by_month())
    span = ledger.date_range()
    if span:
        for key in iter_months(*span):
            by_month.setdefault(key, Money.zero(ledger.currency))
        by_month = dict(sorted(by_month.items()))
        period = f"{span[0].isoformat()} to {span[1].isoformat()}"
    else:
        period = "empty"
    return Summary(
        count=len(ledger),
        income=income,
        spending=spending,
        net=income + spending,
        by_category=dict(ledger.totals_by_category()),
        by_month=by_month,
        period=period,
    )


def top_payees(ledger: Ledger, limit: int = 5) -> list[tuple[str, Money]]:
    spend = ledger.filter(lambda t: t.is_expense).totals_by(lambda t: t.payee)
    ranked = sorted(spend.items(), key=lambda kv: (kv[1].amount, kv[0]))
    return ranked[:limit]


def format_summary(
    ledger: Ledger,
    locale: type[NumberLocale],
    title: str = "Ledger summary",
    by: str = "category",
) -> str:
    s = summarize(ledger)
    head = render(
        "summary.txt",
        title=title,
        underline="=" * len(title),
        source=ledger.source or "-",
        period=s.period,
        count=s.count,
        income=locale.money(s.income),
        spending=locale.money(s.spending),
        net=locale.money(s.net),
    )
    buckets = s.by_month if by == "month" else s.by_category
    rows = [[truncate(k, 32), locale.money(v)] for k, v in buckets.items()]
    table = render_table([by.capitalize(), "Total"], rows, ["left", "right"])
    payees = top_payees(ledger)
    lines = [head.rstrip(), "", table]
    if payees:
        lines += ["", "Top spending:"]
        lines += [f"  {truncate(name, 28):<28} {locale.money(amount):>14}" for name, amount in payees]
    return "\n".join(lines) + "\n"
