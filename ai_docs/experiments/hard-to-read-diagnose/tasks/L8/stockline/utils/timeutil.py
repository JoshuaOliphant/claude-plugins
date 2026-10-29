"""Clock abstraction so imports can be replayed with a fixed time."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

_FEED_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class FixedClock:
    """Clock that returns a fixed instant, optionally ticking per call."""

    def __init__(self, at: datetime, step: timedelta | None = None):
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        self._at = at
        self._step = step

    def now(self) -> datetime:
        current = self._at
        if self._step:
            self._at = self._at + self._step
        return current


def iso(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def feed_date_from_name(filename: str) -> date | None:
    """Suppliers name their drops ``<prefix>_YYYY-MM-DD.<ext>``."""
    m = _FEED_DATE.search(filename)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def run_id_for(ts: datetime, supplier_code: str) -> str:
    return f"{supplier_code.lower()}-{ts.astimezone(timezone.utc):%Y%m%dT%H%M%S}"
