"""Decimal helpers.

All monetary and weight arithmetic in freightdesk is done with
:class:`decimal.Decimal`; floats never enter the rating path.
"""

from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")
ZERO = Decimal("0")


def to_decimal(value, field: str = "value") -> Decimal:
    """Parse ``value`` into a Decimal, accepting ``,`` as decimal separator."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        value = repr(value)
    text = str(value).strip().replace(",", ".")
    try:
        result = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"invalid {field}: {value!r}") from exc
    if not result.is_finite():
        raise ValueError(f"invalid {field}: {value!r}")
    return result


def quantize(value: Decimal, exp: str | Decimal = CENT) -> Decimal:
    """Round half-up to the given exponent (default: cents)."""
    return value.quantize(Decimal(exp), rounding=ROUND_HALF_UP)


def round_up_to_step(value: Decimal, step: Decimal) -> Decimal:
    """Round ``value`` up to the next multiple of ``step``.

    >>> round_up_to_step(Decimal("4.01"), Decimal("0.5"))
    Decimal('4.5')
    """
    if step <= 0:
        raise ValueError("step must be positive")
    units = (value / step).to_integral_value(rounding=ROUND_CEILING)
    return (units * step).normalize() if units else ZERO


def percent_of(amount: Decimal, pct: Decimal) -> Decimal:
    return quantize(amount * pct / Decimal(100))


def plain(value: Decimal) -> str:
    """Render a Decimal without exponent notation or trailing zeros."""
    text = format(value.normalize(), "f")
    return text if text != "-0" else "0"
