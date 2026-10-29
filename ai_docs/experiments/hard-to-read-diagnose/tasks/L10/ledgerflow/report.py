"""Summaries of a written ledger."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from itertools import tee
from typing import Iterable

from ledgerflow.models import Transaction
from ledgerflow.money import quantize
from ledgerflow.utils.dates import month_key


@dataclass
class Summary:
    base_currency: str
    count: int = 0
    inflow: Decimal = Decimal(0)
    outflow: Decimal = Decimal(0)
    by_account: dict[str, Decimal] = field(default_factory=dict)
    by_category: dict[str, Decimal] = field(default_factory=dict)
    by_month: dict[str, int] = field(default_factory=dict)
    sources: dict[str, int] = field(default_factory=dict)

    @property
    def net(self) -> Decimal:
        return self.inflow + self.outflow


def summarize(transactions: Iterable[Transaction], base_currency: str = "USD") -> Summary:
    totals_it, breakdown_it = tee(transactions)
    summary = Summary(base_currency)

    for txn in totals_it:
        summary.count += 1
        value = txn.amount_base.amount
        if value >= 0:
            summary.inflow += value
        else:
            summary.outflow += value

    accounts: dict[str, Decimal] = defaultdict(Decimal)
    categories: dict[str, Decimal] = defaultdict(Decimal)
    months: dict[str, int] = defaultdict(int)
    sources: dict[str, int] = defaultdict(int)
    for txn in breakdown_it:
        accounts[txn.account] += txn.amount_base.amount
        categories[txn.category] += txn.amount_base.amount
        months[month_key(txn.posted)] += 1
        sources[txn.source] += 1

    summary.by_account = {k: quantize(v, base_currency) for k, v in sorted(accounts.items())}
    summary.by_category = {k: quantize(v, base_currency)
                           for k, v in sorted(categories.items(), key=lambda kv: kv[1])}
    summary.by_month = dict(sorted(months.items()))
    summary.sources = dict(sorted(sources.items()))
    return summary


def render(summary: Summary) -> str:
    cur = summary.base_currency
    lines = [
        f"transactions: {summary.count}",
        f"inflow:  {quantize(summary.inflow, cur):>14,} {cur}",
        f"outflow: {quantize(summary.outflow, cur):>14,} {cur}",
        f"net:     {quantize(summary.net, cur):>14,} {cur}",
        "",
        "by source:",
    ]
    lines += [f"  {name:<20} {n:>6}" for name, n in summary.sources.items()]
    lines += ["", "by account:"]
    lines += [f"  {name:<20} {v:>14,}" for name, v in summary.by_account.items()]
    lines += ["", "by category:"]
    lines += [f"  {name:<20} {v:>14,}" for name, v in summary.by_category.items()]
    lines += ["", "by month:"]
    lines += [f"  {name:<20} {n:>6}" for name, n in summary.by_month.items()]
    return "\n".join(lines)
