"""Exact money arithmetic in integer minor units."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

# ISO 4217 exponents for the currencies the offices trade in.
EXPONENTS = {
    "USD": 2,
    "GBP": 2,
    "EUR": 2,
    "INR": 2,
    "SGD": 2,
    "JPY": 0,
}

SYMBOLS = {"USD": "$", "GBP": "£", "EUR": "€", "INR": "₹", "SGD": "S$", "JPY": "¥"}


class CurrencyMismatch(ValueError):
    pass


def exponent(currency: str) -> int:
    try:
        return EXPONENTS[currency]
    except KeyError:
        raise ValueError(f"unsupported currency {currency!r}") from None


@dataclass(frozen=True, order=True)
class Money:
    minor: int
    currency: str

    @classmethod
    def zero(cls, currency: str) -> "Money":
        exponent(currency)
        return cls(0, currency)

    @classmethod
    def parse(cls, text: str, currency: str) -> "Money":
        """Parse a decimal amount such as ``"1299.50"`` into minor units."""
        places = exponent(currency)
        quantum = Decimal(1).scaleb(-places)
        amount = Decimal(text.strip().replace(",", "")).quantize(quantum, rounding=ROUND_HALF_EVEN)
        return cls(int(amount.scaleb(places)), currency)

    def _check(self, other: "Money") -> None:
        if not isinstance(other, Money):
            raise TypeError(f"cannot combine Money with {type(other).__name__}")
        if other.currency != self.currency:
            raise CurrencyMismatch(f"{self.currency} vs {other.currency}")

    def __add__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.minor + other.minor, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.minor - other.minor, self.currency)

    def __neg__(self) -> "Money":
        return Money(-self.minor, self.currency)

    def __bool__(self) -> bool:
        return self.minor != 0

    def scaled(self, factor: Decimal) -> "Money":
        value = (Decimal(self.minor) * factor).quantize(Decimal(1), rounding=ROUND_HALF_EVEN)
        return Money(int(value), self.currency)

    def convert(self, rate: Decimal, target: str) -> "Money":
        """Convert at ``rate`` units of ``target`` per unit of this currency."""
        source_places = exponent(self.currency)
        target_places = exponent(target)
        major = Decimal(self.minor).scaleb(-source_places) * rate
        minor = major.scaleb(target_places).quantize(Decimal(1), rounding=ROUND_HALF_EVEN)
        return Money(int(minor), target)

    def as_decimal(self) -> Decimal:
        return Decimal(self.minor).scaleb(-exponent(self.currency))

    def format(self, symbol: bool = False) -> str:
        places = exponent(self.currency)
        text = f"{self.as_decimal():,.{places}f}"
        if symbol:
            sign = "-" if self.minor < 0 else ""
            return f"{sign}{SYMBOLS.get(self.currency, '')}{text.lstrip('-')}"
        return text

    def to_json(self) -> str:
        return f"{self.as_decimal():.{exponent(self.currency)}f}"

    def __str__(self) -> str:
        return f"{self.format()} {self.currency}"


def total(amounts, currency: str) -> Money:
    result = Money.zero(currency)
    for amount in amounts:
        result = result + amount
    return result
