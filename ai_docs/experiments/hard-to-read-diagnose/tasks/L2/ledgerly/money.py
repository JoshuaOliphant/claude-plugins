"""Money value type built on :class:`decimal.Decimal`.

Amounts are kept as exact decimals. Rounding to cents happens explicitly,
at the points where a business rule says it should (line amounts, tax),
never implicitly on every operation.
"""

from __future__ import annotations

import decimal
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from functools import total_ordering

CENT = Decimal("0.01")
_PARSE_PRECISION = 28
_CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP"}


class CurrencyMismatch(ValueError):
    """Raised when combining amounts in different currencies."""


class AmountFormatError(ValueError):
    """Raised when a textual amount cannot be parsed."""


def parse_amount(text: str) -> Decimal:
    """Parse a human-entered amount such as ``"1,249.50"`` or ``"(12.00)"``.

    Accounting exports write negatives in parentheses and sometimes keep the
    currency symbol; both are accepted.
    """
    cleaned = text.strip()
    negative = False
    if cleaned.startswith("(") and cleaned.endswith(")"):
        negative = True
        cleaned = cleaned[1:-1].strip()
    if cleaned.startswith("-"):
        negative = not negative
        cleaned = cleaned[1:].strip()
    for symbol in _CURRENCY_SYMBOLS:
        cleaned = cleaned.replace(symbol, "")
    cleaned = cleaned.replace(",", "").replace(" ", "")
    if not cleaned:
        raise AmountFormatError(f"empty amount: {text!r}")
    with decimal.localcontext() as ctx:
        ctx.prec = _PARSE_PRECISION
        try:
            value = ctx.create_decimal(cleaned)
        except decimal.InvalidOperation as exc:
            raise AmountFormatError(f"not a number: {text!r}") from exc
    if not value.is_finite():
        raise AmountFormatError(f"not a finite amount: {text!r}")
    return -value if negative else value


def currency_from_symbol(text: str, default: str) -> str:
    for symbol, code in _CURRENCY_SYMBOLS.items():
        if symbol in text:
            return code
    return default


@total_ordering
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))
        object.__setattr__(self, "currency", self.currency.upper())

    @classmethod
    def zero(cls, currency: str = "USD") -> "Money":
        return cls(Decimal("0.00"), currency)

    @classmethod
    def parse(cls, text: str, currency: str = "USD") -> "Money":
        return cls(parse_amount(text), currency_from_symbol(text, currency))

    def _check(self, other: "Money") -> None:
        if not isinstance(other, Money):
            raise TypeError(f"expected Money, got {type(other).__name__}")
        if other.currency != self.currency:
            raise CurrencyMismatch(f"{self.currency} vs {other.currency}")

    def __add__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.amount + other.amount, self.currency)

    def __radd__(self, other):
        if other == 0:
            return self
        return NotImplemented

    def __sub__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.amount - other.amount, self.currency)

    def __neg__(self) -> "Money":
        return Money(-self.amount, self.currency)

    def __mul__(self, factor) -> "Money":
        if isinstance(factor, Money):
            raise TypeError("cannot multiply two Money values")
        if not isinstance(factor, Decimal):
            factor = Decimal(str(factor))
        return Money(self.amount * factor, self.currency)

    __rmul__ = __mul__

    def __lt__(self, other: "Money") -> bool:
        self._check(other)
        return self.amount < other.amount

    def is_zero(self) -> bool:
        return self.amount == 0

    def is_negative(self) -> bool:
        return self.amount < 0

    def rounded(self) -> "Money":
        return Money(self.amount.quantize(CENT, rounding=ROUND_HALF_UP), self.currency)

    def __str__(self) -> str:
        return f"{self.amount:.2f} {self.currency}"


def total(amounts, currency: str = "USD") -> Money:
    """Sum an iterable of Money values, returning zero for an empty input."""
    result = Money.zero(currency)
    for amount in amounts:
        result = result + amount
    return result
