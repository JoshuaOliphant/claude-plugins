"""Markdown report export."""

from __future__ import annotations

from ledgerkit.exporters.base import Exporter
from ledgerkit.formatting.numbers import get_locale
from ledgerkit.formatting.templates import render
from ledgerkit.models import Ledger
from ledgerkit.utils.text import escape_markdown_cell


def describe_period(ledger: Ledger) -> str:
    span = ledger.date_range()
    if not span:
        return "no transactions"
    start, end = span
    if start == end:
        return start.isoformat()
    return f"{start.isoformat()} – {end.isoformat()}"


class MarkdownExporter(Exporter):
    format_name = "markdown"
    aliases = ("md",)
    extensions = (".md", ".markdown")
    description = "A readable Markdown report with per-category totals"
    template = "report.md"

    def format_amount(self, money) -> str:
        return get_locale(self.options.locale).money(money)

    def render(self, ledger: Ledger) -> str:
        rows = []
        for txn, _ in self.rows(ledger):
            cells = [
                self.format_date(txn),
                escape_markdown_cell(txn.payee),
                escape_markdown_cell(txn.account),
                escape_markdown_cell(txn.category),
                self.format_amount(txn.amount),
            ]
            rows.append("| " + " | ".join(cells) + " |")
        category_rows = [
            f"| {escape_markdown_cell(cat)} | {self.format_amount(amount)} |"
            for cat, amount in ledger.totals_by_category().items()
        ]
        return render(
            self.template,
            title=self.options.title,
            source=ledger.source or "-",
            count=len(ledger),
            period=describe_period(ledger),
            rows="\n".join(rows),
            total=self.format_amount(ledger.balance()),
            category_rows="\n".join(category_rows),
        )
