"""Euro reference exchange rates.

Rates come from ``data/fx/eurofxref-hist.csv`` (ECB-style layout: a ``Date``
column followed by one column per currency, quoted as units per EUR).  For a
given day the most recent published rate on or before that day applies.
"""

from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal

from freightdesk.config import load_settings
from freightdesk.domain.errors import DataError
from freightdesk.utils.decimals import to_decimal
from freightdesk.utils.diskcache import memoize_to_disk

_TABLE: list[tuple[date, dict[str, str]]] | None = None


def _table() -> list[tuple[date, dict[str, str]]]:
    global _TABLE
    if _TABLE is None:
        path = load_settings().fx_file
        rows: list[tuple[date, dict[str, str]]] = []
        try:
            with path.open(newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    day = date.fromisoformat(row.pop("Date").strip())
                    rows.append((day, {k.strip(): v.strip() for k, v in row.items() if v and v.strip()}))
        except FileNotFoundError:
            raise DataError(f"exchange rate file missing: {path}") from None
        rows.sort(key=lambda item: item[0])
        _TABLE = rows
    return _TABLE


@memoize_to_disk("fx")
def reference_rate(currency: str, on: str) -> str:
    """Units of ``currency`` per EUR published on or before ISO date ``on``."""
    currency = currency.upper()
    if currency == "EUR":
        return "1"
    day = date.fromisoformat(on)
    best: str | None = None
    for published, rates in _table():
        if published > day:
            break
        if currency in rates:
            best = rates[currency]
    if best is None:
        raise DataError(f"no {currency} reference rate on or before {on}")
    return best


def rate(currency: str, on: date) -> Decimal:
    return to_decimal(reference_rate(currency, on.isoformat()), "rate")


def known_currencies() -> list[str]:
    seen = {"EUR"}
    for _, rates in _table():
        seen.update(rates)
    return sorted(seen)
