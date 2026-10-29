"""Quote currency conversion."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

from freightdesk.adapters import fx_rates
from freightdesk.domain.money import Money
from freightdesk.domain.quote import Quote, QuoteLine


def convert_quote(quote: Quote, currency: str, on: date) -> Quote:
    """Return a copy of ``quote`` with every line converted from its currency.

    Lines are converted individually (and rounded to cents) so that the
    converted total equals the sum of the converted lines, as on the invoice.
    """
    currency = currency.upper()
    if currency == quote.currency:
        return quote
    if quote.currency != "EUR":
        raise ValueError("only EUR-denominated quotes can be converted")
    fx = fx_rates.rate(currency, on)
    lines = [
        QuoteLine(line.code, line.description, line.amount.converted(fx, currency), line.parcel_index)
        for line in quote.lines
    ]
    return replace(quote, currency=currency, lines=lines, fx_rate=fx)


def converted_amount(amount: Money, currency: str, on: date) -> Money:
    if currency == amount.currency:
        return amount
    return amount.converted(fx_rates.rate(currency, on), currency)
