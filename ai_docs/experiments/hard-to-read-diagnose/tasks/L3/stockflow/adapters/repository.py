"""In-process store of stock levels and the movement journal."""

from __future__ import annotations

import threading
from typing import Iterable, Iterator

from stockflow.domain.models import Movement, StockLevel


class InMemoryStockRepository:
    """Holds every warehouse/SKU balance plus the journal of posted movements.

    All mutation happens under one lock; readers get copies so a report can
    be built while ingestion is still running.
    """

    def __init__(self, opening: Iterable[StockLevel] = ()) -> None:
        self._lock = threading.Lock()
        self._levels: dict[tuple[str, str], StockLevel] = {}
        self._seen: set[tuple[str, str, str]] = set()
        self._journal: list[Movement] = []
        for level in opening:
            self._levels[(level.warehouse, level.sku)] = level.copy()

    def _level_for(self, warehouse: str, sku: str) -> StockLevel:
        key = (warehouse, sku)
        if key not in self._levels:
            self._levels[key] = StockLevel(warehouse=warehouse, sku=sku)
        return self._levels[key]

    def record(self, movement: Movement) -> bool:
        """Apply a movement. Returns False if it was already recorded."""
        with self._lock:
            key = movement.dedup_key
            if key in self._seen:
                return False
            self._seen.add(key)
            self._level_for(movement.warehouse, movement.sku).apply(movement)
            self._journal.append(movement)
            return True

    def record_many(self, movements: Iterable[Movement]) -> tuple[int, int]:
        posted = duplicates = 0
        for movement in movements:
            if self.record(movement):
                posted += 1
            else:
                duplicates += 1
        return posted, duplicates

    def level(self, warehouse: str, sku: str) -> StockLevel:
        with self._lock:
            found = self._levels.get((warehouse, sku))
            return found.copy() if found else StockLevel(warehouse=warehouse, sku=sku)

    def levels(self) -> list[StockLevel]:
        with self._lock:
            return [lvl.copy() for _, lvl in sorted(self._levels.items())]

    def journal(self) -> list[Movement]:
        with self._lock:
            return list(self._journal)

    def __iter__(self) -> Iterator[StockLevel]:
        return iter(self.levels())

    @property
    def movement_count(self) -> int:
        with self._lock:
            return len(self._journal)

    def warehouses(self) -> list[str]:
        with self._lock:
            return sorted({wh for wh, _ in self._levels})
