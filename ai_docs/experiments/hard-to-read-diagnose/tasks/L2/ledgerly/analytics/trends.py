"""Month-over-month revenue trends for the summary report."""

from __future__ import annotations

import decimal
from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping, Sequence

from ..money import Money
from ..utils.dates import iter_month_keys

GROWTH_PRECISION = 8
_HUNDRED = Decimal(100)


def _growth_context() -> decimal.Context:
    ctx = decimal.getcontext()
    ctx.prec = GROWTH_PRECISION
    ctx.rounding = decimal.ROUND_HALF_EVEN
    return ctx


_CTX = _growth_context()


@dataclass(frozen=True)
class MonthPoint:
    month: str
    revenue: Money
    growth_pct: Decimal | None


def growth(previous: Money, current: Money) -> Decimal | None:
    """Percentage change from ``previous`` to ``current``; None when undefined."""
    if previous.is_zero():
        return None
    change = _CTX.subtract(current.amount, previous.amount)
    return _CTX.multiply(_CTX.divide(change, previous.amount), _HUNDRED)


def monthly_series(monthly: Mapping[str, Money], currency: str) -> list[MonthPoint]:
    """Fill gaps with zero months and attach growth versus the prior month."""
    if not monthly:
        return []
    keys = sorted(monthly)
    series: list[MonthPoint] = []
    previous: Money | None = None
    for key in iter_month_keys(keys[0], keys[-1]):
        revenue = monthly.get(key, Money.zero(currency))
        pct = growth(previous, revenue) if previous is not None else None
        series.append(MonthPoint(key, revenue, pct))
        previous = revenue
    return series


def average_growth(series: Sequence[MonthPoint]) -> Decimal | None:
    """Compound monthly growth rate between the first and last month."""
    if len(series) < 2:
        return None
    first, last = series[0].revenue.amount, series[-1].revenue.amount
    if first <= 0 or last <= 0:
        return None
    periods = Decimal(len(series) - 1)
    ratio = _CTX.divide(last, first)
    rate = _CTX.power(ratio, _CTX.divide(Decimal(1), periods))
    return _CTX.multiply(_CTX.subtract(rate, Decimal(1)), _HUNDRED)


def best_and_worst(series: Sequence[MonthPoint]) -> tuple[MonthPoint, MonthPoint] | None:
    if not series:
        return None
    ranked = sorted(series, key=lambda point: (point.revenue.amount, point.month))
    return ranked[-1], ranked[0]


def streak(series: Sequence[MonthPoint]) -> int:
    """Length of the current run of consecutive growing months."""
    count = 0
    for point in reversed(series):
        if point.growth_pct is None or point.growth_pct <= 0:
            break
        count += 1
    return count
