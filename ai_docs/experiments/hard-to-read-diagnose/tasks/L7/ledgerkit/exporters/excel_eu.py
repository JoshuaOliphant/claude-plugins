"""CSV dialect understood by spreadsheet applications in continental Europe.

Those applications expect ``;`` between fields because ``,`` is the decimal
separator, a byte-order mark so that UTF-8 is detected, and CRLF line ends.
"""

from ledgerkit.exporters.delimited import DelimitedExporter


class ExcelEuropeExporter(DelimitedExporter):
    format_name = "excel-eu"
    aliases = ("csv-eu", "excel")
    description = "Semicolon-separated CSV with decimal comma for European spreadsheets"
    delimiter = ";"
    decimal_separator = ","
    line_terminator = "\r\n"
    write_bom = True
    default_date_format = "%d.%m.%Y"
