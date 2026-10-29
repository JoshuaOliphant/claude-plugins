"""A minimal money type."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from freightdesk.utils.decimals import CENT, ZERO, quantize, to_decimal

CURRENCIES = {"EUR", "CHF", "GBP", "PLN", "DKK", "SEK", "USD", "CZK"}


@dataclass(frozen=True, order=True)
class Money:
    amount: Decimal
    currency: str = "EUR"

    def __post_init__(self):
        if self.currency not in CURRENCIES:
            raise ValueError(f"unknown currency {self.currency!r}")
        object.__setattr__(self, "amount", quantize(to_decimal(self.amount, "amount"), CENT))

    @classmethod
    def zero(cls, currency: str = "EUR") -> "Money":
        return cls(ZERO, currency)

    def _check(self, other: "Money") -> None:
        if not isinstance(other, Money):
            raise TypeError(f"cannot combine Money with {type(other).__name__}")
        if other.currency != self.currency:
            raise ValueError(f"currency mismatch: {self.currency} vs {other.currency}")

    def __add__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor) -> "Money":
        return Money(self.amount * to_decimal(factor, "factor"), self.currency)

    __rmul__ = __mul__

    def converted(self, rate: Decimal, currency: str) -> "Money":
        return Money(self.amount * rate, currency)

    def __str__(self) -> str:
        return f"{self.currency} {self.amount:.2f}"

    def to_json(self) -> dict:
        return {"amount": f"{self.amount:.2f}", "currency": self.currency}


def total(items, currency: str = "EUR") -> Money:
    result = Money.zero(currency)
    for item in items:
        result = result + item
    return result
