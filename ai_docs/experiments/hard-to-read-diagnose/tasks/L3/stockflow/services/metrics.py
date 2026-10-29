"""Process-wide counters and timers for a run."""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from typing import Iterator


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: dict[str, int] = {}
        self._timings: dict[str, float] = {}

    def incr(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counts[name] = self._counts.get(name, 0) + amount

    def count(self, name: str) -> int:
        with self._lock:
            return self._counts.get(name, 0)

    @contextmanager
    def timer(self, name: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            with self._lock:
                self._timings[name] = self._timings.get(name, 0.0) + elapsed

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "counts": dict(sorted(self._counts.items())),
                "timings": {k: round(v, 4) for k, v in sorted(self._timings.items())},
            }
