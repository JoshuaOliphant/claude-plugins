"""Decimal money helpers. Floats never touch amounts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation

_MINOR_UNITS = {"JPY": 0, "KRW": 0, "BHD": 3, "KWD": 3}
_CLEAN = re.compile(r"[\s,_']")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


class MoneyError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if not _CURRENCY_RE.match(self.currency):
            raise MoneyError(f"not an ISO currency code: {self.currency!r}")

    def __add__(self, other: "Money") -> "Money":
        self._same(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._same(other)
        return Money(self.amount - other.amount, self.currency)

    def __neg__(self) -> "Money":
        return Money(-self.amount, self.currency)

    def _same(self, other: "Money") -> None:
        if other.currency != self.currency:
            raise MoneyError(f"currency mismatch: {self.currency} vs {other.currency}")

    def rounded(self) -> "Money":
        return Money(quantize(self.amount, self.currency), self.currency)

    def is_zero(self) -> bool:
        return self.amount == 0

    def __str__(self) -> str:
        return f"{self.amount:,.{minor_units(self.currency)}f} {self.currency}"


def minor_units(currency: str) -> int:
    return _MINOR_UNITS.get(currency, 2)


def quantize(value: Decimal, currency: str) -> Decimal:
    exp = Decimal(1).scaleb(-minor_units(currency))
    return value.quantize(exp, rounding=ROUND_HALF_EVEN)


def parse_amount(text: str | int | float | Decimal) -> Decimal:
    """Parse an amount as written by banks: ``1,234.50``, ``(12.00)``, ``-3``."""
    if isinstance(text, Decimal):
        return text
    if isinstance(text, (int, float)):
        return Decimal(str(text))
    raw = _CLEAN.sub("", text.strip())
    negative = False
    if raw.startswith("(") and raw.endswith(")"):
        negative, raw = True, raw[1:-1]
    if raw.endswith("-"):
        negative, raw = True, raw[:-1]
    if not raw:
        raise MoneyError("empty amount")
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise MoneyError(f"unparseable amount: {text!r}") from exc
    if not value.is_finite():
        raise MoneyError(f"non-finite amount: {text!r}")
    return -value if negative else value


def total(items, currency: str) -> Money:
    acc = Money(Decimal(0), currency)
    for item in items:
        acc = acc + item
    return acc
