"""Sales-tax rules.

Tax is charged per invoice on the subtotal and rounded half-up to the cent,
which is what the regional authorities expect on printed invoices.
"""

from __future__ import annotations

import decimal
from decimal import Decimal

from .money import CENT, Money

_TAX_CONTEXT = decimal.Context(prec=28, rounding=decimal.ROUND_HALF_UP)
EXEMPT = "EXEMPT"


class UnknownRegion(KeyError):
    """Raised when a customer's region has no configured rate."""


def rate_for(region: str, rates, default_region: str = "") -> Decimal:
    """Return the tax rate for ``region``, falling back to the default region."""
    key = (region or default_region).upper()
    if key == EXEMPT:
        return Decimal("0")
    try:
        return rates[key]
    except KeyError:
        raise UnknownRegion(key) from None


def compute_tax(subtotal: Money, rate: Decimal) -> Money:
    if rate == 0 or subtotal.is_zero():
        return Money.zero(subtotal.currency)
    raw = _TAX_CONTEXT.multiply(subtotal.amount, rate)
    return Money(raw.quantize(CENT, context=_TAX_CONTEXT), subtotal.currency)


def effective_rate(subtotal: Money, tax: Money) -> Decimal:
    """Rate actually charged after rounding, for audit listings."""
    if subtotal.is_zero():
        return Decimal("0")
    return _TAX_CONTEXT.divide(tax.amount, subtotal.amount).quantize(
        Decimal("0.0001"), context=_TAX_CONTEXT
    )
