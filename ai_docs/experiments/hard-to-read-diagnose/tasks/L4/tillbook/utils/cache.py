"""A tiny bounded memo cache.

Report builders ask for the same office/day combination repeatedly (a weekly
report touches every day, the item report touches them again), so the ledger
memoises its lookups. Keys must be hashable and fully describe the query.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Callable, Generic, Hashable, TypeVar

V = TypeVar("V")


class BoundedCache(Generic[V]):
    def __init__(self, capacity: int = 256) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self._capacity = capacity
        self._entries: OrderedDict[Hashable, V] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def __len__(self) -> int:
        return len(self._entries)

    def __contains__(self, key: Hashable) -> bool:
        return key in self._entries

    def get_or_compute(self, key: Hashable, compute: Callable[[], V]) -> V:
        if key in self._entries:
            self.hits += 1
            self._entries.move_to_end(key)
            return self._entries[key]
        self.misses += 1
        value = compute()
        self._entries[key] = value
        if len(self._entries) > self._capacity:
            self._entries.popitem(last=False)
        return value

    def invalidate(self, predicate: Callable[[Hashable], bool] | None = None) -> int:
        """Drop entries whose key matches ``predicate`` (all if omitted)."""
        if predicate is None:
            dropped = len(self._entries)
            self._entries.clear()
            return dropped
        doomed = [key for key in self._entries if predicate(key)]
        for key in doomed:
            del self._entries[key]
        return len(doomed)

    def stats(self) -> dict[str, int]:
        return {"size": len(self._entries), "hits": self.hits, "misses": self.misses}
