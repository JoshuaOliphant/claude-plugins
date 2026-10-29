"""Date parsing and period helpers."""

from __future__ import annotations

import calendar
import datetime as _dt
import re
from typing import Iterator

INPUT_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y", "%m/%d/%Y", "%Y%m%d")

_PERIOD_RE = re.compile(r"^(?P<year>\d{4})(?:-(?P<month>\d{1,2}))?$")
_QUARTER_RE = re.compile(r"^(?P<year>\d{4})-?Q(?P<q>[1-4])$", re.IGNORECASE)


class DateParseError(ValueError):
    pass


def parse_date(value) -> _dt.date:
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    text = str(value).strip()
    for fmt in INPUT_FORMATS:
        try:
            return _dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise DateParseError(f"unrecognised date: {value!r}")


def format_date(value: _dt.date, fmt: str | None = None) -> str:
    if not fmt:
        return value.isoformat()
    return value.strftime(fmt)


def month_key(value: _dt.date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def month_bounds(year: int, month: int) -> tuple[_dt.date, _dt.date]:
    last = calendar.monthrange(year, month)[1]
    return _dt.date(year, month, 1), _dt.date(year, month, last)


def parse_period(text: str) -> tuple[_dt.date, _dt.date]:
    """Turn ``2026``, ``2026-03`` or ``2026Q2`` into an inclusive date range."""
    text = text.strip()
    match = _QUARTER_RE.match(text)
    if match:
        year = int(match.group("year"))
        q = int(match.group("q"))
        start, _ = month_bounds(year, 3 * q - 2)
        _, end = month_bounds(year, 3 * q)
        return start, end
    match = _PERIOD_RE.match(text)
    if not match:
        raise DateParseError(f"unrecognised period: {text!r}")
    year = int(match.group("year"))
    if match.group("month"):
        month = int(match.group("month"))
        if not 1 <= month <= 12:
            raise DateParseError(f"month out of range in {text!r}")
        return month_bounds(year, month)
    return _dt.date(year, 1, 1), _dt.date(year, 12, 31)


def iter_months(start: _dt.date, end: _dt.date) -> Iterator[str]:
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        yield f"{year:04d}-{month:02d}"
        month += 1
        if month > 12:
            month = 1
            year += 1
