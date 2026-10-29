"""Token-bucket limiter for outgoing batches."""

from __future__ import annotations

from typing import Protocol


class Clock(Protocol):
    def now(self) -> float: ...
    def sleep(self, seconds: float) -> None: ...


class TokenBucket:
    def __init__(self, per_minute: int, burst: int, clock: Clock):
        if per_minute < 1 or burst < 1:
            raise ValueError("per_minute and burst must be positive")
        self.rate = per_minute / 60.0
        self.capacity = float(burst)
        self.tokens = float(burst)
        self.clock = clock
        self.updated = clock.now()
        self.waits = 0

    def _refill(self) -> None:
        now = self.clock.now()
        elapsed = max(now - self.updated, 0.0)
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.updated = now

    def try_acquire(self) -> bool:
        self._refill()
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    def acquire(self) -> None:
        while not self.try_acquire():
            deficit = 1.0 - self.tokens
            self.waits += 1
            self.clock.sleep(deficit / self.rate)
