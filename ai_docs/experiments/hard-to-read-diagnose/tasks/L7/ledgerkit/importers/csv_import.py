"""Import from CSV files exported by banks or by ledgerkit itself."""

from __future__ import annotations

import csv
import io

from ledgerkit.importers.base import Importer, ImportError_, register_importer

COLUMN_SYNONYMS = {
    "date": ("date", "booking date", "transaction date", "datum"),
    "payee": ("payee", "description", "name", "counterparty"),
    "account": ("account", "account name"),
    "category": ("category", "kategorie"),
    "amount": ("amount", "value", "betrag"),
    "currency": ("currency", "ccy"),
    "memo": ("memo", "note", "notes", "reference"),
    "tags": ("tags",),
    "id": ("id", "transaction id"),
}


def _sniff_dialect(sample: str):
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        return csv.excel


def _map_header(header: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    lowered = [h.strip().lower() for h in header]
    for field_name, synonyms in COLUMN_SYNONYMS.items():
        for i, name in enumerate(lowered):
            if name in synonyms:
                mapping[field_name] = i
                break
    return mapping


@register_importer("csv", extensions=(".csv",))
class CsvImporter(Importer):
    def parse(self, text, source, report):
        text = text.lstrip("﻿")
        dialect = _sniff_dialect(text[:4096])
        reader = csv.reader(io.StringIO(text), dialect)
        try:
            header = next(reader)
        except StopIteration:
            return
        mapping = _map_header(header)
        missing = [f for f in ("date", "amount") if f not in mapping]
        if missing:
            raise ImportError_(source, 1, f"missing column(s): {', '.join(missing)}")
        for lineno, row in enumerate(reader, start=2):
            if not any(cell.strip() for cell in row):
                continue
            fields = {name: row[idx] for name, idx in mapping.items() if idx < len(row)}
            txn = self.build(source, lineno, report, **fields)
            if txn is not None:
                yield txn
