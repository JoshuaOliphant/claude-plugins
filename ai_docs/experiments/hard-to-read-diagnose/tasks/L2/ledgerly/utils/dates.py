"""Date helpers used by loaders and reports."""

from __future__ import annotations

from datetime import date, datetime
from typing import Iterator

_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y")


class DateFormatError(ValueError):
    pass


def parse_date(text: str) -> date:
    """Parse the date formats seen in our CSV exports."""
    value = text.strip()
    for fmt in _FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise DateFormatError(f"unrecognised date: {text!r}")


def today() -> date:
    return date.today()


def month_key(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def parse_month_key(key: str) -> tuple[int, int]:
    year, month = key.split("-")
    return int(year), int(month)


def next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def iter_month_keys(first: str, last: str) -> Iterator[str]:
    """Yield every month key from ``first`` to ``last`` inclusive."""
    year, month = parse_month_key(first)
    end = parse_month_key(last)
    while (year, month) <= end:
        yield f"{year:04d}-{month:02d}"
        year, month = next_month(year, month)


def quarter_of(day: date) -> str:
    return f"{day.year}-Q{(day.month - 1) // 3 + 1}"


def days_overdue(due: date, as_of: date) -> int:
    return max(0, (as_of - due).days)
