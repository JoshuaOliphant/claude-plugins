"""Business-date helpers.

The business date can be pinned with ``STOCKROOM_TODAY`` (``YYYY-MM-DD``) so
that a back-office clerk replaying yesterday's paperwork stamps documents
with yesterday's date.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta

ENV_TODAY = "STOCKROOM_TODAY"


def parse_date(raw: str) -> date:
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"invalid date {raw!r}, expected YYYY-MM-DD") from exc


def today() -> date:
    raw = os.environ.get(ENV_TODAY)
    if raw:
        return parse_date(raw)
    return date.today()


def as_date(value: str | date | None) -> date | None:
    if value is None or isinstance(value, date):
        return value
    return parse_date(value[:10])


def window_start(days: int, end: date | None = None) -> date:
    end = end or today()
    return end - timedelta(days=days)


def age_in_days(since: date, until: date | None = None) -> int:
    until = until or today()
    return (until - since).days


def timestamp() -> str:
    """Local wall-clock timestamp used for log lines and export headers."""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
