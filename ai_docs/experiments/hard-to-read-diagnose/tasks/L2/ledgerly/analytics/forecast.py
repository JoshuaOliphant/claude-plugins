"""Naive next-month revenue forecast.

This is a planning aid, not accounting: it works in floats and reports whole
currency units with a rough spread band.
"""

from __future__ import annotations

import random
import statistics
from dataclasses import dataclass
from typing import Sequence

from .trends import MonthPoint

_BOOTSTRAP_SAMPLES = 200
_rng = random.Random(1729)


@dataclass(frozen=True)
class Forecast:
    month: str
    expected: float
    low: float
    high: float
    window: int


def _next_key(month: str) -> str:
    year, mon = (int(part) for part in month.split("-"))
    year, mon = (year + 1, 1) if mon == 12 else (year, mon + 1)
    return f"{year:04d}-{mon:02d}"


def moving_average(values: Sequence[float], window: int) -> float:
    tail = list(values)[-window:]
    return statistics.fmean(tail) if tail else 0.0


def bootstrap_band(values: Sequence[float], window: int) -> tuple[float, float]:
    tail = list(values)[-window:]
    if len(tail) < 2:
        only = tail[0] if tail else 0.0
        return only, only
    _rng.seed(len(tail))
    means = sorted(
        statistics.fmean(_rng.choices(tail, k=len(tail))) for _ in range(_BOOTSTRAP_SAMPLES)
    )
    low = means[int(0.1 * len(means))]
    high = means[int(0.9 * len(means)) - 1]
    return low, high


def next_month(series: Sequence[MonthPoint], window: int = 3) -> Forecast | None:
    if not series:
        return None
    values = [float(point.revenue.amount) for point in series]
    expected = moving_average(values, window)
    low, high = bootstrap_band(values, window)
    return Forecast(
        month=_next_key(series[-1].month),
        expected=round(expected),
        low=round(min(low, expected)),
        high=round(max(high, expected)),
        window=min(window, len(values)),
    )
