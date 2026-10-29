"""JSON and JSON Lines exports."""

from __future__ import annotations

import json

from ledgerkit.exporters.base import Exporter
from ledgerkit.models import Ledger


class JsonExporter(Exporter):
    format_name = "json"
    extensions = (".json",)
    description = "A JSON document with ledger metadata and a list of transactions"
    indent = 2

    def record(self, txn, balance=None) -> dict:
        record = {col: self.cell(txn, col) for col in self.options.columns}
        if "tags" in record:
            record["tags"] = list(txn.tags)
        if balance is not None:
            record["balance"] = self.format_amount(balance)
        return record

    def render(self, ledger: Ledger) -> str:
        span = ledger.date_range()
        document = {
            "source": ledger.source,
            "currency": ledger.currency,
            "count": len(ledger),
            "from": span[0].isoformat() if span else None,
            "to": span[1].isoformat() if span else None,
            "transactions": [self.record(t, b) for t, b in self.rows(ledger)],
        }
        return json.dumps(document, indent=self.indent, ensure_ascii=False) + "\n"


class JsonLinesExporter(JsonExporter):
    format_name = "jsonl"
    aliases = ("ndjson",)
    extensions = (".jsonl", ".ndjson")
    description = "One JSON object per transaction per line"

    def render(self, ledger: Ledger) -> str:
        lines = [
            json.dumps(self.record(t, b), ensure_ascii=False, sort_keys=False)
            for t, b in self.rows(ledger)
        ]
        return "\n".join(lines) + ("\n" if lines else "")
