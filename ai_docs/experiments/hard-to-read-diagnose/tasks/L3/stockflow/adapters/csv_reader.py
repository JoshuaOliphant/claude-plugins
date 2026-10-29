"""Read movement exports produced by the warehouse management systems.

Exports differ between sites: some use semicolons, some tabs, header names
vary ("qty" vs "quantity"), and a few prepend a UTF-8 BOM. Everything is
normalised here so validation only ever sees canonical field names.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Iterator

from stockflow.domain.errors import InputFormatError
from stockflow.domain.models import RawRow

CANONICAL_FIELDS = ("date", "warehouse", "sku", "kind", "quantity", "uom", "reference")

_HEADER_ALIASES = {
    "movement_date": "date",
    "posting_date": "date",
    "txn_date": "date",
    "wh": "warehouse",
    "site": "warehouse",
    "location": "warehouse",
    "item": "sku",
    "item_code": "sku",
    "article": "sku",
    "type": "kind",
    "movement_type": "kind",
    "qty": "quantity",
    "amount": "quantity",
    "unit": "uom",
    "unit_of_measure": "uom",
    "ref": "reference",
    "document": "reference",
    "doc_no": "reference",
}

REQUIRED_FIELDS = ("date", "warehouse", "sku", "kind", "quantity", "reference")


def canonical_header(name: str) -> str:
    key = name.strip().lower().replace(" ", "_").replace("-", "_")
    return _HEADER_ALIASES.get(key, key)


class MovementCsvReader:
    def __init__(self, sample_size: int = 4096) -> None:
        self.sample_size = sample_size

    def _dialect(self, sample: str, path: Path) -> type[csv.Dialect] | csv.Dialect:
        if path.suffix.lower() == ".tsv":
            return csv.excel_tab
        try:
            return csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            return csv.excel

    def read_text(self, text: str, source: str, path: Path | None = None) -> Iterator[RawRow]:
        if text.startswith("﻿"):
            text = text[1:]
        lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
        if not lines:
            raise InputFormatError(f"{source}: file is empty")
        body = "\n".join(lines)
        dialect = self._dialect(body[: self.sample_size], path or Path(source))
        reader = csv.reader(io.StringIO(body), dialect)
        header = [canonical_header(h) for h in next(reader)]
        missing = [f for f in REQUIRED_FIELDS if f not in header]
        if missing:
            raise InputFormatError(f"{source}: missing columns {', '.join(missing)}")
        for offset, values in enumerate(reader, start=2):
            if len(values) < len(header):
                values = values + [""] * (len(header) - len(values))
            fields = {name: values[i].strip() for i, name in enumerate(header)}
            fields.setdefault("uom", "")
            yield RawRow(source=source, line_no=offset, fields=fields)

    def read(self, path: Path) -> Iterator[RawRow]:
        try:
            with open(path, encoding="utf-8", newline="") as fh:
                text = fh.read()
        except UnicodeDecodeError:
            with open(path, encoding="latin-1", newline="") as fh:
                text = fh.read()
        return self.read_text(text, path.name, path)
