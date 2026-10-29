"""Time helpers.  All timestamps inside relaydesk are timezone-aware UTC."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso(text: str) -> datetime:
    """Parse an ISO-8601 timestamp.  Naive values are treated as UTC, which
    is what the help-desk export emits."""
    value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def format_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def age(created: datetime, now: datetime) -> timedelta:
    return now - created


def humanize(delta: timedelta) -> str:
    seconds = int(delta.total_seconds())
    if seconds < 0:
        return "in the future"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"


def stamp(now: datetime | None = None) -> str:
    """Filesystem-safe timestamp used for outbox file names."""
    return (now or utcnow()).strftime("%Y%m%dT%H%M%S")


class MonotonicClock:
    def now(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)


class ManualClock:
    """Clock that only advances when told to; used for dry runs."""

    def __init__(self, start: float = 0.0):
        self._now = start
        self.slept = 0.0

    def now(self) -> float:
        return self._now

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            self._now += seconds
            self.slept += seconds
