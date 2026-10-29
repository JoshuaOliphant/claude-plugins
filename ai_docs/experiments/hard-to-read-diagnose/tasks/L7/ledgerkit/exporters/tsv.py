"""Tab-separated export, convenient for pasting into spreadsheets."""

import csv

from ledgerkit.exporters.delimited import DelimitedExporter


class TsvExporter(DelimitedExporter):
    format_name = "tsv"
    aliases = ("tab",)
    extensions = (".tsv", ".tab")
    description = "Tab-separated values"
    delimiter = "\t"
    quoting = csv.QUOTE_NONE
    escapechar = "\\"

    def cell(self, txn, column, balance=None) -> str:
        return super().cell(txn, column, balance).replace("\t", " ")
