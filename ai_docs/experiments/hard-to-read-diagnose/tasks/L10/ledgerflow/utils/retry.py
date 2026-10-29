"""Retry with exponential backoff.

``retry_call`` takes a zero-argument callable and invokes it again for every
attempt, so whatever the callable builds (connections, readers, iterators) is
built fresh each time.
"""

from __future__ import annotations

import functools
import logging
import time
from dataclasses import dataclass
from typing import Callable, Iterator, TypeVar

T = TypeVar("T")
log = logging.getLogger(__name__)


class RetryExhausted(RuntimeError):
    def __init__(self, attempts: int, last: BaseException):
        super().__init__(f"gave up after {attempts} attempts: {last}")
        self.attempts = attempts
        self.last = last


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 3
    backoff_seconds: float = 0.5
    multiplier: float = 2.0
    max_backoff_seconds: float = 30.0
    retry_on: tuple[type[BaseException], ...] = (OSError,)

    def delays(self) -> Iterator[float]:
        """Delay before attempt 2, 3, ... (one fewer than ``attempts``)."""
        delay = self.backoff_seconds
        for _ in range(self.attempts - 1):
            yield min(delay, self.max_backoff_seconds)
            delay *= self.multiplier

    @classmethod
    def from_config(cls, cfg, retry_on: tuple[type[BaseException], ...]) -> "RetryPolicy":
        return cls(cfg.attempts, cfg.backoff_seconds, cfg.multiplier, cfg.max_backoff_seconds, retry_on)


@dataclass
class AttemptLog:
    attempts: int = 0
    errors: list[str] | None = None

    def record(self, exc: BaseException) -> None:
        if self.errors is None:
            self.errors = []
        self.errors.append(f"{type(exc).__name__}: {exc}")


def retry_call(
    fn: Callable[[], T],
    policy: RetryPolicy,
    *,
    sleep: Callable[[float], None] = time.sleep,
    on_retry: Callable[[int, BaseException, float], None] | None = None,
    attempt_log: AttemptLog | None = None,
) -> T:
    delays = policy.delays()
    attempt = 0
    while True:
        attempt += 1
        if attempt_log is not None:
            attempt_log.attempts = attempt
        try:
            return fn()
        except policy.retry_on as exc:
            if attempt_log is not None:
                attempt_log.record(exc)
            delay = next(delays, None)
            if delay is None:
                raise RetryExhausted(attempt, exc) from exc
            if on_retry is not None:
                on_retry(attempt, exc, delay)
            else:
                log.warning("attempt %d failed (%s); retrying in %.2fs", attempt, exc, delay)
            sleep(delay)


def retrying(policy: RetryPolicy, *, sleep: Callable[[float], None] = time.sleep):
    """Decorator form of :func:`retry_call` for functions with plain arguments."""

    def wrap(fn):
        @functools.wraps(fn)
        def inner(*args, **kwargs):
            return retry_call(lambda: fn(*args, **kwargs), policy, sleep=sleep)

        return inner

    return wrap
