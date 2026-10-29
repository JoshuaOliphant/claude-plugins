"""Public holiday calendars used for transit-time estimates.

Only nationwide holidays are modelled; regional holidays are ignored because
carriers route around them on a best-effort basis.
"""

from __future__ import annotations

from datetime import date, timedelta

from freightdesk.utils.diskcache import memoize_to_disk

SUPPORTED = ("DE", "AT", "CH", "FR", "NL")


def easter_sunday(year: int) -> date:
    """Gregorian Easter Sunday (anonymous Gregorian algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def _movable(year: int) -> dict[str, date]:
    easter = easter_sunday(year)
    return {
        "good_friday": easter - timedelta(days=2),
        "easter_monday": easter + timedelta(days=1),
        "ascension": easter + timedelta(days=39),
        "whit_monday": easter + timedelta(days=50),
        "corpus_christi": easter + timedelta(days=60),
    }


def _kings_day(year: int) -> date:
    day = date(year, 4, 27)
    # Moved to the 26th when the 27th is a Sunday.
    return day - timedelta(days=1) if day.weekday() == 6 else day


@memoize_to_disk("holidays")
def public_holidays(country: str, year: int) -> list[str]:
    """ISO dates of nationwide public holidays for ``country`` in ``year``."""
    country = country.upper()
    if country not in SUPPORTED:
        raise ValueError(f"no holiday calendar for {country!r}")
    mv = _movable(year)
    fixed = {
        "DE": [(1, 1), (5, 1), (10, 3), (12, 25), (12, 26)],
        "AT": [(1, 1), (1, 6), (5, 1), (8, 15), (10, 26), (11, 1), (12, 8), (12, 25), (12, 26)],
        "CH": [(1, 1), (8, 1), (12, 25), (12, 26)],
        "FR": [(1, 1), (5, 1), (5, 8), (7, 14), (8, 15), (11, 1), (11, 11), (12, 25)],
        "NL": [(1, 1), (12, 25), (12, 26)],
    }[country]
    movable = {
        "DE": ["good_friday", "easter_monday", "ascension", "whit_monday"],
        "AT": ["easter_monday", "ascension", "whit_monday", "corpus_christi"],
        "CH": ["good_friday", "easter_monday", "ascension", "whit_monday"],
        "FR": ["easter_monday", "ascension", "whit_monday"],
        "NL": ["good_friday", "easter_monday", "ascension", "whit_monday"],
    }[country]
    days = {date(year, m, d) for m, d in fixed}
    days.update(mv[name] for name in movable)
    if country == "NL":
        days.add(_kings_day(year))
        if year % 5 == 0:
            days.add(date(year, 5, 5))
    return sorted(d.isoformat() for d in days)


def is_business_day(country: str, day: date) -> bool:
    if day.weekday() >= 5:
        return False
    return day.isoformat() not in public_holidays(country, day.year)


def add_business_days(country: str, start: date, days: int) -> date:
    """The date ``days`` business days after ``start`` in ``country``."""
    current = start
    remaining = days
    while remaining > 0:
        current += timedelta(days=1)
        if is_business_day(country, current):
            remaining -= 1
    return current
