"""Date parsing for the assorted formats our sources use."""

from __future__ import annotations

from datetime import date, datetime, timezone

_FALLBACK_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%Y%m%d", "%d.%m.%Y")


class DateError(ValueError):
    pass


def parse_date(text: str, fmt: str | None = None) -> date:
    text = text.strip()
    if not text:
        raise DateError("empty date")
    if fmt:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError as exc:
            raise DateError(f"{text!r} does not match {fmt!r}") from exc
    for candidate in _FALLBACK_FORMATS:
        try:
            return datetime.strptime(text, candidate).date()
        except ValueError:
            continue
    raise DateError(f"unrecognised date {text!r}")


def parse_timestamp_date(text: str) -> date:
    """Posting date of an ISO-8601 timestamp, taken in UTC."""
    raw = text.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        ts = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise DateError(f"bad timestamp {text!r}") from exc
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).date()


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"
