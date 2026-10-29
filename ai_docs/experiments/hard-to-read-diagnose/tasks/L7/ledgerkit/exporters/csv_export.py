"""RFC 4180 style CSV export."""

from ledgerkit.exporters.delimited import DelimitedExporter


class CsvExporter(DelimitedExporter):
    format_name = "csv"
    aliases = ("comma",)
    description = "Comma-separated values, ISO dates, dot decimal separator"
