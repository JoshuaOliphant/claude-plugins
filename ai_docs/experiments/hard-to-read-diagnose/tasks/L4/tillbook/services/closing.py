"""End-of-day close status.

A trading day is considered closed for reporting once the office's local
clock has passed midnight plus a grace period, which gives late refunds from
the payment provider time to settle.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from tillbook.domain.offices import Office, OfficeRegistry
from tillbook.utils.timeconv import UTC, format_iso

DEFAULT_GRACE = timedelta(hours=2)


@dataclass(frozen=True)
class CloseStatus:
    office: str
    day: date
    closes_at: datetime
    closed: bool

    def to_json(self) -> dict:
        return {"office": self.office, "date": self.day.isoformat(),
                "closes_at": format_iso(self.closes_at), "closed": self.closed}


def close_time(office: Office, day: date, grace: timedelta = DEFAULT_GRACE) -> datetime:
    _, end = office.day_bounds(day)
    return end + grace


def status(office: Office, day: date, now: datetime | None = None,
           grace: timedelta = DEFAULT_GRACE) -> CloseStatus:
    now = now or datetime.now(UTC)
    closes_at = close_time(office, day, grace)
    return CloseStatus(office.code, day, closes_at, now >= closes_at)


def latest_closed_day(office: Office, now: datetime | None = None,
                      grace: timedelta = DEFAULT_GRACE) -> date:
    now = now or datetime.now(UTC)
    candidate = (now - grace).astimezone(office.tz).date() - timedelta(days=1)
    while not status(office, candidate, now, grace).closed:
        candidate -= timedelta(days=1)
    return candidate


def board(offices: OfficeRegistry, day: date, now: datetime | None = None) -> list[CloseStatus]:
    now = now or datetime.now(UTC)
    return [status(office, day, now) for office in offices]
