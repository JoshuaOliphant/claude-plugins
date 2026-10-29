"""In-process audit journal of order handling events.

The journal keeps the most recent events so operators can inspect what the
service did (``python -m basketry summarize --journal``).  Event details are
snapshotted through JSON when recorded, so later changes to the objects they
came from do not alter history.
"""

from __future__ import annotations

import json
from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class JournalEntry:
    sequence: int
    event: str
    order_id: str
    details: dict[str, Any]

    def describe(self) -> str:
        parts = ", ".join(f"{k}={v}" for k, v in sorted(self.details.items()))
        return f"#{self.sequence:04d} {self.event:<10} {self.order_id} {parts}".rstrip()


class Journal:
    def __init__(self, capacity: int = 500):
        self._capacity = capacity
        self._entries: deque[JournalEntry] = deque(maxlen=capacity)
        self._sequence = 0

    def record(self, event: str, order_id: str, **details: Any) -> JournalEntry:
        self._sequence += 1
        snapshot = json.loads(json.dumps(details, default=str))
        entry = JournalEntry(self._sequence, event, order_id, snapshot)
        self._entries.append(entry)
        return entry

    def __iter__(self) -> Iterator[JournalEntry]:
        return iter(list(self._entries))

    def __len__(self) -> int:
        return len(self._entries)

    def for_order(self, order_id: str) -> list[JournalEntry]:
        return [e for e in self._entries if e.order_id == order_id]

    def events(self, event: str) -> list[JournalEntry]:
        return [e for e in self._entries if e.event == event]

    def reset(self) -> None:
        self._entries = deque(maxlen=self._capacity)
        self._sequence = 0
