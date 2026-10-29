"""Conversions between epoch seconds, datetimes and ISO-8601 strings.

All instants inside Tillbook are timezone-aware datetimes in UTC or plain
integer epoch seconds. Office-local wall time only appears at the edges
(report headers, calendar dates), see ``tillbook.domain.offices``.
"""

from __future__ import annotations

import calendar
import re
import time
from datetime import date, datetime, timedelta, timezone

UTC = timezone.utc

_ISO_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})"
    r"[T ](?P<time>\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?)"
    r"(?P<offset>Z|[+-]\d{2}:?\d{2})?$"
)


class TimestampError(ValueError):
    """Raised when a timestamp cannot be interpreted unambiguously."""


def from_epoch(seconds: int | float) -> datetime:
    """Return the aware UTC datetime for ``seconds`` since the epoch."""
    return datetime.fromtimestamp(seconds, tz=UTC)


def to_epoch(moment: datetime) -> int:
    """Return whole epoch seconds for ``moment``."""
    if moment.tzinfo is None:
        raise TimestampError(f"naive datetime {moment!r} has no defined instant")
    return int(time.mktime(moment.timetuple()))


def utc_epoch(moment: datetime) -> int:
    """Return whole epoch seconds for an instant given in UTC."""
    if moment.tzinfo is not None:
        moment = moment.astimezone(UTC)
    return calendar.timegm(moment.timetuple())


def parse_iso(text: str, *, assume_utc: bool = False) -> datetime:
    """Parse an ISO-8601 timestamp into an aware UTC datetime.

    Strings without an offset are rejected unless ``assume_utc`` is set,
    because a bare wall-clock time does not identify an instant.
    """
    text = text.strip()
    match = _ISO_RE.match(text)
    if not match:
        raise TimestampError(f"not an ISO-8601 timestamp: {text!r}")
    offset = match.group("offset")
    if offset is None:
        if not assume_utc:
            raise TimestampError(f"timestamp {text!r} has no UTC offset")
        normalised = f"{match.group('date')}T{match.group('time')}+00:00"
    elif offset == "Z":
        normalised = f"{match.group('date')}T{match.group('time')}+00:00"
    else:
        if ":" not in offset:
            offset = offset[:3] + ":" + offset[3:]
        normalised = f"{match.group('date')}T{match.group('time')}{offset}"
    return datetime.fromisoformat(normalised).astimezone(UTC)


def format_iso(moment: datetime) -> str:
    """Format an aware datetime as compact ISO-8601 with a ``Z`` suffix."""
    if moment.tzinfo is None:
        raise TimestampError(f"naive datetime {moment!r} cannot be formatted")
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_date(text: str) -> date:
    try:
        return date.fromisoformat(text.strip())
    except ValueError as exc:
        raise TimestampError(f"not a calendar date: {text!r}") from exc


def date_range(first: date, last: date) -> list[date]:
    """Inclusive list of calendar dates from ``first`` to ``last``."""
    if last < first:
        raise ValueError(f"{last} is before {first}")
    days = (last - first).days
    return [first + timedelta(days=offset) for offset in range(days + 1)]


def week_start(day: date, first_weekday: int = 0) -> date:
    """Return the first day of the week containing ``day``.

    ``first_weekday`` follows ``date.weekday()``: 0 is Monday, 6 is Sunday.
    """
    shift = (day.weekday() - first_weekday) % 7
    return day - timedelta(days=shift)
