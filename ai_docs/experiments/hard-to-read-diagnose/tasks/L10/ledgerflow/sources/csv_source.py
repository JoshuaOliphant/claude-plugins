"""Bank statement CSV exports."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Iterator

from ledgerflow.sources.base import RawRecord, Source
from ledgerflow.utils.iterators import peek

log = logging.getLogger(__name__)

# Header aliases seen across the banks we import from.
COLUMN_ALIASES = {
    "record_id": ("reference", "ref", "transaction id", "id"),
    "posted": ("date", "posting date", "booked", "value date"),
    "amount": ("amount", "value", "amt"),
    "currency": ("currency", "ccy"),
    "account": ("account", "account name", "iban"),
    "memo": ("description", "memo", "narrative", "details"),
}


class CsvSource(Source):
    kind = "csv"

    def __init__(self, name: str, path: Path, *, date_format: str | None = None,
                 delimiter: str | None = None, encoding: str = "utf-8-sig",
                 default_currency: str | None = None):
        super().__init__(name)
        self.path = Path(path)
        self.date_format = date_format
        self.delimiter = delimiter
        self.encoding = encoding
        self.default_currency = default_currency

    def records(self) -> Iterator[RawRecord]:
        with open(self.path, newline="", encoding=self.encoding) as fh:
            dialect = self._dialect(fh)
            reader = csv.DictReader(fh, dialect=dialect)
            first, rows = peek(reader)
            if first is None:
                log.info("%s: empty statement", self.path)
                return
            mapping = self._map_columns(reader.fieldnames or [])
            for row in rows:
                yield self._to_record(row, mapping, reader.line_num)

    def _dialect(self, fh):
        if self.delimiter:
            class Fixed(csv.excel):
                delimiter = self.delimiter

            return Fixed
        sample = fh.read(4096)
        fh.seek(0)
        try:
            return csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            return csv.excel

    def _map_columns(self, fieldnames: list[str]) -> dict[str, str]:
        lowered = {name.strip().lower(): name for name in fieldnames}
        mapping: dict[str, str] = {}
        for target, aliases in COLUMN_ALIASES.items():
            for alias in aliases:
                if alias in lowered:
                    mapping[target] = lowered[alias]
                    break
        return mapping

    def _to_record(self, row: dict[str, str], mapping: dict[str, str], line: int) -> RawRecord:
        def get(field_name: str) -> str:
            column = mapping.get(field_name)
            return (row.get(column) or "").strip() if column else ""

        return RawRecord(
            record_id=get("record_id") or f"{self.name}-L{line}",
            posted=get("posted"),
            amount=get("amount"),
            currency=(get("currency") or self.default_currency or "").upper(),
            account=get("account"),
            memo=get("memo"),
            date_format=self.date_format,
            line=line,
        )
