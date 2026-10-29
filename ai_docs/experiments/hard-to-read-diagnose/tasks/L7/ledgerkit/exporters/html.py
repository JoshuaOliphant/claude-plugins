"""Standalone HTML report export."""

from __future__ import annotations

from ledgerkit.exporters.base import Exporter
from ledgerkit.exporters.markdown import describe_period
from ledgerkit.formatting.numbers import get_locale
from ledgerkit.formatting.templates import render
from ledgerkit.models import Ledger
from ledgerkit.utils.text import escape_html


class HtmlExporter(Exporter):
    format_name = "html"
    aliases = ("htm",)
    extensions = (".html", ".htm")
    description = "A self-contained HTML page"
    template = "report.html"

    def format_amount(self, money) -> str:
        return get_locale(self.options.locale).money(money)

    def row(self, txn) -> str:
        css = "expense" if txn.is_expense else "income"
        cells = "".join(
            f"<td>{escape_html(value)}</td>"
            for value in (self.format_date(txn), txn.payee, txn.account, txn.category)
        )
        amount = escape_html(self.format_amount(txn.amount))
        return f'<tr class="{css}">{cells}<td class="amount">{amount}</td></tr>'

    def render(self, ledger: Ledger) -> str:
        lang = (self.options.locale or "en").split("_", 1)[0]
        if lang == "C":
            lang = "en"
        return render(
            self.template,
            lang=escape_html(lang),
            title=escape_html(self.options.title),
            source=escape_html(ledger.source or "-"),
            count=len(ledger),
            period=escape_html(describe_period(ledger)),
            rows="\n".join(self.row(t) for t, _ in self.rows(ledger)),
            total=escape_html(self.format_amount(ledger.balance())),
        )
