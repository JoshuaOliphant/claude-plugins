"""Foreign-exchange conversion from a daily rates table."""

from __future__ import annotations

import bisect
import csv
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from ledgerflow.money import Money, quantize

log = logging.getLogger(__name__)

# Rates files are a few hundred KB and never change during a run.
_TABLES: dict[tuple[Path, float], "RateTable"] = {}

MAX_STALENESS = timedelta(days=7)


class FxError(LookupError):
    pass


@dataclass
class _Series:
    dates: list[date] = field(default_factory=list)
    rates: list[Decimal] = field(default_factory=list)

    def add(self, d: date, rate: Decimal) -> None:
        i = bisect.bisect_left(self.dates, d)
        if i < len(self.dates) and self.dates[i] == d:
            self.rates[i] = rate
        else:
            self.dates.insert(i, d)
            self.rates.insert(i, rate)

    def on_or_before(self, d: date) -> tuple[date, Decimal] | None:
        i = bisect.bisect_right(self.dates, d)
        if i == 0:
            return None
        return self.dates[i - 1], self.rates[i - 1]


class RateTable:
    """``usd_per_unit`` rates by currency and day; cross rates go via USD."""

    def __init__(self, pivot: str = "USD"):
        self.pivot = pivot
        self._series: dict[str, _Series] = {}

    def add(self, currency: str, day: date, usd_per_unit: Decimal) -> None:
        self._series.setdefault(currency, _Series()).add(day, usd_per_unit)

    def currencies(self) -> set[str]:
        return set(self._series) | {self.pivot}

    def knows(self, currency: str) -> bool:
        return currency == self.pivot or currency in self._series

    def pivot_rate(self, currency: str, day: date) -> Decimal:
        if currency == self.pivot:
            return Decimal(1)
        series = self._series.get(currency)
        if series is None:
            raise FxError(f"no rates for {currency}")
        hit = series.on_or_before(day)
        if hit is None:
            raise FxError(f"no {currency} rate on or before {day}")
        rate_day, rate = hit
        if day - rate_day > MAX_STALENESS:
            raise FxError(f"{currency} rate for {day} is stale (last {rate_day})")
        return rate

    def convert(self, money: Money, target: str, day: date) -> Money:
        if money.currency == target:
            return money
        usd = money.amount * self.pivot_rate(money.currency, day)
        value = usd / self.pivot_rate(target, day)
        return Money(quantize(value, target), target)


def load_rates(path: Path) -> RateTable:
    path = Path(path)
    key = (path.resolve(), path.stat().st_mtime)
    table = _TABLES.get(key)
    if table is None:
        table = _read_rates(path)
        _TABLES[key] = table
        log.debug("loaded fx rates from %s", path)
    return table


def _read_rates(path: Path) -> RateTable:
    table = RateTable()
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            table.add(row["currency"].strip().upper(), date.fromisoformat(row["date"]),
                      Decimal(row["usd_per_unit"]))
    return table
