"""Fixed-point money values.

Amounts are kept as :class:`decimal.Decimal` quantized to the minor unit of
their currency. Arithmetic between different currencies is refused rather
than silently converted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation

CURRENCY_EXPONENTS = {
    "USD": 2,
    "EUR": 2,
    "GBP": 2,
    "CHF": 2,
    "SEK": 2,
    "JPY": 0,
    "KWD": 3,
}

DEFAULT_CURRENCY = "USD"

_AMOUNT_RE = re.compile(r"^\s*(?P<sign>[-+]?)\s*(?P<body>[\d.,' ]+)\s*$")


class MoneyError(ValueError):
    """Raised for malformed amounts or mixed-currency arithmetic."""


def exponent_for(currency: str) -> int:
    return CURRENCY_EXPONENTS.get(currency.upper(), 2)


def _quantum(currency: str) -> Decimal:
    exp = exponent_for(currency)
    return Decimal(1).scaleb(-exp)


@dataclass(frozen=True, order=True)
class Money:
    amount: Decimal
    currency: str = DEFAULT_CURRENCY

    def __post_init__(self) -> None:
        currency = self.currency.upper()
        try:
            amount = Decimal(self.amount)
        except (InvalidOperation, TypeError) as exc:
            raise MoneyError(f"invalid amount {self.amount!r}") from exc
        amount = amount.quantize(_quantum(currency), rounding=ROUND_HALF_EVEN)
        object.__setattr__(self, "amount", amount)
        object.__setattr__(self, "currency", currency)

    @classmethod
    def zero(cls, currency: str = DEFAULT_CURRENCY) -> "Money":
        return cls(Decimal(0), currency)

    def _check(self, other: "Money") -> None:
        if not isinstance(other, Money):
            raise TypeError(f"cannot combine Money with {type(other).__name__}")
        if other.currency != self.currency:
            raise MoneyError(f"currency mismatch: {self.currency} vs {other.currency}")

    def __add__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.amount - other.amount, self.currency)

    def __neg__(self) -> "Money":
        return Money(-self.amount, self.currency)

    def __abs__(self) -> "Money":
        return Money(abs(self.amount), self.currency)

    def __bool__(self) -> bool:
        return bool(self.amount)

    @property
    def is_negative(self) -> bool:
        return self.amount < 0

    def plain(self) -> str:
        """Machine-readable representation: ``-1234.50`` (no grouping, dot decimal)."""
        exp = exponent_for(self.currency)
        return f"{self.amount:.{exp}f}"

    def __str__(self) -> str:
        return f"{self.plain()} {self.currency}"


def parse_amount(text: str, currency: str = DEFAULT_CURRENCY) -> Money:
    """Parse a human-entered amount.

    Accepts ``1234.5``, ``-1,234.50``, ``(12.00)`` for negatives, and
    ``1.234,50`` when the comma is clearly the decimal separator.
    """
    raw = str(text).strip()
    negative = False
    if raw.startswith("(") and raw.endswith(")"):
        negative = True
        raw = raw[1:-1]
    match = _AMOUNT_RE.match(raw)
    if not match:
        raise MoneyError(f"cannot parse amount {text!r}")
    if match.group("sign") == "-":
        negative = not negative
    body = match.group("body").replace(" ", "").replace("'", "")
    if "," in body and "." in body:
        if body.rfind(",") > body.rfind("."):
            body = body.replace(".", "").replace(",", ".")
        else:
            body = body.replace(",", "")
    elif "," in body:
        head, _, tail = body.rpartition(",")
        if len(tail) == 3 and head:
            body = head.replace(",", "") + tail
        else:
            body = head.replace(",", "") + "." + tail
    try:
        value = Decimal(body)
    except InvalidOperation as exc:
        raise MoneyError(f"cannot parse amount {text!r}") from exc
    if negative:
        value = -value
    return Money(value, currency)


def total(values, currency: str = DEFAULT_CURRENCY) -> Money:
    result = Money.zero(currency)
    for value in values:
        result = result + value
    return result
