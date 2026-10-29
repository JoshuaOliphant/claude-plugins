"""Retry with capped exponential backoff."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import TypeVar

from ..settings.coerce import parse_bool
from .ratelimit import Clock

log = logging.getLogger(__name__)
T = TypeVar("T")


class TransientError(RuntimeError):
    """A delivery failure worth retrying (timeouts, 5xx, ...)."""


class RetryPolicy:
    def __init__(self, attempts: int, backoff: float, max_backoff: float, clock: Clock,
                 jitter: bool | None = None):
        self.attempts = attempts
        self.backoff = backoff
        self.max_backoff = max_backoff
        self.clock = clock
        if jitter is None:
            jitter = parse_bool(os.environ.get("RELAYDESK_RETRY_JITTER", "0"))
        self.jitter = jitter
        self._salt = 0

    def delay(self, attempt: int) -> float:
        base = min(self.backoff * (2 ** (attempt - 1)), self.max_backoff)
        if not self.jitter:
            return base
        self._salt = (self._salt * 1103515245 + 12345) % (2 ** 31)
        return base * (0.5 + (self._salt % 1000) / 2000)

    def call(self, fn: Callable[[], T]) -> tuple[T, int]:
        last: Exception | None = None
        for attempt in range(1, self.attempts + 1):
            try:
                return fn(), attempt
            except TransientError as exc:
                last = exc
                log.info("attempt %d/%d failed: %s", attempt, self.attempts, exc)
                if attempt < self.attempts:
                    self.clock.sleep(self.delay(attempt))
        assert last is not None
        raise last
