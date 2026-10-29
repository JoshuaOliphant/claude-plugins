"""Money parsing and rounding.

All prices are ``Decimal`` with two places.  Feeds are messy: costs show
up as ``"1,234.50"``, ``"$4.10"``, ``"4,10"`` (European decimal comma) or
plain floats in JSON.
"""

from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")
_CURRENCY_SYMBOLS = "$€£"


class MoneyParseError(ValueError):
    pass


def parse_money(value) -> Decimal:
    if value is None:
        raise MoneyParseError("missing amount")
    if isinstance(value, Decimal):
        return value.quantize(CENT, ROUND_HALF_UP)
    if isinstance(value, (int, float)):
        return Decimal(str(value)).quantize(CENT, ROUND_HALF_UP)
    text = str(value).strip()
    for sym in _CURRENCY_SYMBOLS:
        text = text.replace(sym, "")
    text = text.replace(" ", "")
    if not text:
        raise MoneyParseError("missing amount")
    if "," in text and "." in text:
        # "1,234.50" -> thousands separator; "1.234,50" -> European
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        head, _, tail = text.rpartition(",")
        text = f"{head}.{tail}" if len(tail) != 3 else head + tail
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise MoneyParseError(f"not a number: {value!r}") from exc
    return amount.quantize(CENT, ROUND_HALF_UP)


def quantize(amount: Decimal) -> Decimal:
    return amount.quantize(CENT, ROUND_HALF_UP)


def apply_ending(amount: Decimal, ending: str) -> Decimal:
    """Round *amount* up to the next price that ends in *ending* (e.g. ``.99``).

    Amounts under one unit are left at cent precision; an empty ending
    disables the rule.
    """
    amount = quantize(amount)
    if not ending or amount < 1:
        return amount
    tail = Decimal(ending)
    whole = amount.to_integral_value(rounding=ROUND_CEILING)
    candidate = whole - 1 + tail
    if candidate < amount:
        candidate += 1
    return quantize(candidate)


def format_money(amount: Decimal, currency: str = "USD") -> str:
    symbol = {"USD": "$", "EUR": "€", "GBP": "£"}.get(currency, "")
    return f"{symbol}{amount:,.2f}" if symbol else f"{amount:,.2f} {currency}"
