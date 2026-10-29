"""Sorted time index over one office's transactions.

Lookups by time window are the hot path for every report, so transactions
are kept sorted by capture instant and windows are resolved with bisection
instead of scanning.
"""

from __future__ import annotations

import bisect
from datetime import datetime
from typing import Iterable, Iterator

from tillbook.domain.models import Transaction
from tillbook.utils.timeconv import from_epoch, to_epoch


class TimeIndex:
    def __init__(self, transactions: Iterable[Transaction] = ()) -> None:
        self._keys: list[tuple[int, str]] = []
        self._rows: list[Transaction] = []
        for txn in transactions:
            self.add(txn)

    def __len__(self) -> int:
        return len(self._rows)

    def __iter__(self) -> Iterator[Transaction]:
        return iter(self._rows)

    def add(self, txn: Transaction) -> None:
        key = (txn.epoch, txn.txn_id)
        position = bisect.bisect_left(self._keys, key)
        if position < len(self._keys) and self._keys[position] == key:
            self._rows[position] = txn
            return
        self._keys.insert(position, key)
        self._rows.insert(position, txn)

    def between_epochs(self, start: int, end: int) -> list[Transaction]:
        """Transactions with ``start <= epoch < end``."""
        if end <= start:
            return []
        low = bisect.bisect_left(self._keys, (start, ""))
        high = bisect.bisect_left(self._keys, (end, ""))
        return self._rows[low:high]

    def between(self, start: datetime, end: datetime) -> list[Transaction]:
        """Transactions captured in the half-open window ``[start, end)``."""
        return self.between_epochs(to_epoch(start), to_epoch(end))

    def first(self) -> Transaction | None:
        return self._rows[0] if self._rows else None

    def last(self) -> Transaction | None:
        return self._rows[-1] if self._rows else None

    def span(self) -> tuple[datetime, datetime] | None:
        if not self._rows:
            return None
        return from_epoch(self._rows[0].epoch), from_epoch(self._rows[-1].epoch)
