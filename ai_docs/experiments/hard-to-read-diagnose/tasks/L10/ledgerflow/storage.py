"""The output ledger: JSON lines, one transaction per line, sorted on close."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Iterable, Iterator

from ledgerflow.models import Transaction
from ledgerflow.utils.iterators import chunked

log = logging.getLogger(__name__)

WRITE_BATCH = 50


class LedgerStore:
    """Collects committed transactions and writes them atomically on ``close``."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._pending: list[Transaction] = []
        self.ids: set[str] = set()
        self.closed = False

    def commit(self, transactions: Iterable[Transaction]) -> int:
        if self.closed:
            raise RuntimeError("ledger already written")
        n = 0
        for txn in transactions:
            self._pending.append(txn)
            self.ids.add(txn.txn_id)
            n += 1
        return n

    def close(self) -> Path:
        if self.closed:
            return self.path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        ordered = sorted(self._pending, key=lambda t: (t.posted, t.source, t.txn_id))
        fd, tmp = tempfile.mkstemp(prefix=".ledger-", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                for batch in chunked(ordered, WRITE_BATCH):
                    fh.write("".join(json.dumps(t.to_dict(), sort_keys=True) + "\n" for t in batch))
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
        self.closed = True
        log.info("wrote %d transactions to %s", len(ordered), self.path)
        return self.path

    def __len__(self) -> int:
        return len(self._pending)


def read_ledger(path: str | Path) -> Iterator[Transaction]:
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield Transaction.from_dict(json.loads(line))
