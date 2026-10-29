"""Card processor exports: one JSON document per line."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Iterator

from ledgerflow.sources.base import RawRecord, Source
from ledgerflow.utils.dates import DateError, parse_timestamp_date

log = logging.getLogger(__name__)


class JsonlSource(Source):
    kind = "jsonl"

    def __init__(self, name: str, path: Path, *, encoding: str = "utf-8"):
        super().__init__(name)
        self.path = Path(path)
        self.encoding = encoding
        self.skipped_lines = 0

    def records(self) -> Iterator[RawRecord]:
        self.skipped_lines = 0
        with open(self.path, encoding=self.encoding) as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line or line.startswith("//"):
                    continue
                try:
                    doc = json.loads(line)
                except json.JSONDecodeError as exc:
                    self.skipped_lines += 1
                    log.warning("%s:%d: unreadable line (%s)", self.path, lineno, exc.msg)
                    continue
                yield self._to_record(doc, lineno)

    def _to_record(self, doc: dict[str, Any], lineno: int) -> RawRecord:
        value = doc.get("value") or {}
        posted = str(doc.get("ts", ""))
        try:
            posted = parse_timestamp_date(posted).isoformat()
        except DateError:
            pass  # the normaliser reports it with the record id attached
        return RawRecord(
            record_id=str(doc.get("txn", "")),
            posted=posted,
            amount=str(value.get("amount", "")),
            currency=str(value.get("ccy", "")).upper(),
            account=str(doc.get("card", "")),
            memo=str(doc.get("merchant", "")),
            line=lineno,
            extra={k: v for k, v in doc.items() if k not in {"txn", "ts", "value", "card", "merchant"}},
        )
