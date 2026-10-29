"""Shared implementation for delimiter-separated exports."""

from __future__ import annotations

import csv
import io

from ledgerkit.exporters.base import Exporter
from ledgerkit.models import Ledger


class DelimitedExporter(Exporter):
    abstract = True
    extensions = (".csv",)
    delimiter = ","
    decimal_separator = "."
    quoting = csv.QUOTE_MINIMAL
    line_terminator = "\n"
    escapechar = None
    write_bom = False
    default_date_format = ""

    def header(self) -> list[str]:
        cols = list(self.options.columns)
        if self.options.running_balance:
            cols.append("balance")
        return cols

    def format_amount(self, money) -> str:
        text = money.plain()
        if self.decimal_separator != ".":
            text = text.replace(".", self.decimal_separator)
        return text

    def format_date(self, txn) -> str:
        fmt = self.options.date_format or self.default_date_format
        return txn.date.strftime(fmt) if fmt else txn.date.isoformat()

    def render(self, ledger: Ledger) -> str:
        buf = io.StringIO()
        if self.write_bom:
            buf.write("\ufeff")
        writer = csv.writer(
            buf,
            delimiter=self.delimiter,
            quoting=self.quoting,
            lineterminator=self.line_terminator,
            escapechar=self.escapechar,
        )
        writer.writerow(self.header())
        for txn, balance in self.rows(ledger):
            row = [self.cell(txn, col) for col in self.options.columns]
            if balance is not None:
                row.append(self.format_amount(balance))
            writer.writerow(row)
        return buf.getvalue()
