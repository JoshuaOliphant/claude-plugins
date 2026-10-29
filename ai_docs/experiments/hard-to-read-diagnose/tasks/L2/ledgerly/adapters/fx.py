"""Foreign-exchange conversion into the reporting currency.

Rates come from ``data/fx_rates.json`` as month-end rates per currency,
expressed as units of the base currency per one unit of foreign currency.
Conversion uses the rate for the invoice's issue month, falling back to the
most recent earlier month.
"""

from __future__ import annotations

import bisect
import decimal
import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from ..money import CENT, Money
from ..utils.cache import file_memo
from ..utils.dates import month_key

FX_CONTEXT = decimal.Context(prec=28, rounding=decimal.ROUND_HALF_EVEN)


class MissingRate(LookupError):
    pass


@dataclass
class RateTable:
    base: str
    rates: dict[str, dict[str, Decimal]] = field(default_factory=dict)

    def months(self, currency: str) -> list[str]:
        return sorted(self.rates.get(currency, {}))

    def rate(self, currency: str, month: str) -> Decimal:
        currency = currency.upper()
        if currency == self.base:
            return Decimal(1)
        months = self.months(currency)
        if not months:
            raise MissingRate(f"no rates for {currency}")
        index = bisect.bisect_right(months, month) - 1
        if index < 0:
            raise MissingRate(f"no {currency} rate on or before {month}")
        return self.rates[currency][months[index]]

    def convert(self, money: Money, month: str) -> Money:
        if money.currency == self.base:
            return money
        rate = self.rate(money.currency, month)
        converted = FX_CONTEXT.multiply(money.amount, rate)
        return Money(converted.quantize(CENT, context=FX_CONTEXT), self.base)

    def convert_on(self, money: Money, day) -> Money:
        return self.convert(money, month_key(day))


@file_memo
def load_rates(path) -> RateTable:
    with Path(path).open(encoding="utf-8") as handle:
        raw = json.load(handle)
    table = RateTable(base=raw["base"].upper())
    for currency, by_month in raw["rates"].items():
        table.rates[currency.upper()] = {
            month: Decimal(str(value)) for month, value in by_month.items()
        }
    return table


def identity_table(base: str) -> RateTable:
    return RateTable(base=base.upper())
