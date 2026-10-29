"""Read the payment provider's refund settlement CSV."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Iterator

from tillbook.adapters.codec import DecodeError, decode_refund_row
from tillbook.domain.models import Transaction

log = logging.getLogger(__name__)

REQUIRED_COLUMNS = ("refund_id", "office", "amount", "currency", "processed_at")


class RefundCsvSource:
    def __init__(self, path: Path, strict: bool = False) -> None:
        self.path = path
        self.strict = strict
        self.rejected: list[DecodeError] = []

    def __iter__(self) -> Iterator[Transaction]:
        if not self.path.exists():
            log.info("no refund file at %s", self.path)
            return
        with self.path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
            if missing:
                raise DecodeError(f"refund file missing columns: {', '.join(missing)}",
                                  where=self.path.name)
            for row in reader:
                where = f"{self.path.name}:{reader.line_num}"
                try:
                    yield decode_refund_row(row, source=where)
                except DecodeError as error:
                    if self.strict:
                        raise
                    self.rejected.append(error)
                    log.warning("skipping %s", error)
