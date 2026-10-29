"""Duplicate suppression for feeds.

Some supplier exports repeat a line when a page boundary in their export
job is retried.  Repeats are always adjacent or nearly so, so a short
sliding window is enough to catch them.
"""

from __future__ import annotations

from collections import deque
from typing import Hashable


class RecentWindow:
    def __init__(self, size: int = 64):
        self.size = size
        self._items: deque = deque(maxlen=size)

    def seen(self, item: Hashable) -> bool:
        """Return True if *item* was offered within the window; remember it."""
        if item in self._items:
            return True
        self._items.append(item)
        return False

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)
