"""Reference FX rates.

The treasury team publishes one closing rate per currency per UTC date; a
transaction converts at the rate of the UTC date on which it was captured.
"""

from __future__ import annotations

import bisect
import csv
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from tillbook.domain.money import Money
from tillbook.utils.timeconv import UTC, from_epoch, parse_date


class MissingRate(LookupError):
    pass


class FxTable:
    def __init__(self, base: str = "USD") -> None:
        self.base = base
        self._dates: dict[str, list[date]] = {}
        self._rates: dict[str, list[Decimal]] = {}

    @classmethod
    def load(cls, path: Path, base: str = "USD") -> "FxTable":
        table = cls(base)
        if not path.exists():
            return table
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                table.add(parse_date(row["date"]), row["currency"].strip().upper(),
                          Decimal(row["per_usd"]))
        return table

    def add(self, day: date, currency: str, per_base: Decimal) -> None:
        dates = self._dates.setdefault(currency, [])
        rates = self._rates.setdefault(currency, [])
        index = bisect.bisect_left(dates, day)
        if index < len(dates) and dates[index] == day:
            rates[index] = per_base
        else:
            dates.insert(index, day)
            rates.insert(index, per_base)

    def rate_on(self, currency: str, day: date) -> Decimal:
        """Units of ``currency`` per base unit, latest published on or before ``day``."""
        if currency == self.base:
            return Decimal(1)
        dates = self._dates.get(currency)
        if not dates:
            raise MissingRate(f"no rates for {currency}")
        index = bisect.bisect_right(dates, day) - 1
        if index < 0:
            raise MissingRate(f"no {currency} rate on or before {day}")
        return self._rates[currency][index]

    def convert(self, amount: Money, when: datetime | int, target: str | None = None) -> Money:
        target = target or self.base
        if amount.currency == target:
            return amount
        moment = from_epoch(when) if isinstance(when, int) else when.astimezone(UTC)
        day = moment.date()
        to_base = Decimal(1) / self.rate_on(amount.currency, day)
        in_base = amount.convert(to_base, self.base)
        if target == self.base:
            return in_base
        return in_base.convert(self.rate_on(target, day), target)
