"""Import from JSON documents and JSON Lines files."""

from __future__ import annotations

import json

from ledgerkit.importers.base import Importer, ImportError_, register_importer


def _records_from_document(doc, source):
    if isinstance(doc, list):
        return doc
    if isinstance(doc, dict) and isinstance(doc.get("transactions"), list):
        return doc["transactions"]
    raise ImportError_(source, 1, "expected a list or an object with a 'transactions' list")


@register_importer("json", extensions=(".json",))
class JsonImporter(Importer):
    def records(self, text, source):
        try:
            doc = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ImportError_(source, exc.lineno, exc.msg) from exc
        for index, record in enumerate(_records_from_document(doc, source), start=1):
            yield index, record

    def parse(self, text, source, report):
        for index, record in self.records(text, source):
            if not isinstance(record, dict):
                raise ImportError_(source, index, "transaction must be an object")
            fields = {k: ("" if v is None else v) for k, v in record.items()}
            if isinstance(fields.get("amount"), (int, float)):
                fields["amount"] = repr(fields["amount"])
            txn = self.build(source, index, report, **fields)
            if txn is not None:
                yield txn


@register_importer("jsonl", extensions=(".jsonl", ".ndjson"))
class JsonLinesImporter(JsonImporter):
    def records(self, text, source):
        for lineno, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                yield lineno, json.loads(line)
            except json.JSONDecodeError as exc:
                raise ImportError_(source, lineno, exc.msg) from exc
