"""Date parsing for the various formats warehouse systems export."""

from __future__ import annotations

import re
from datetime import date, datetime

_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y", "%Y%m%d")
_US_STYLE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


def parse_date(raw: str) -> date:
    text = raw.strip()
    if not text:
        raise ValueError("empty date")
    if "T" in text:
        text = text.split("T", 1)[0]
    m = _US_STYLE.match(text)
    if m:
        month, day, year = (int(g) for g in m.groups())
        return date(year, month, day)
    for fmt in _FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date {raw!r}")


def iso(d: date | None) -> str:
    return d.isoformat() if d is not None else ""


def latest(dates) -> date | None:
    best = None
    for d in dates:
        if d is not None and (best is None or d > best):
            best = d
    return best
