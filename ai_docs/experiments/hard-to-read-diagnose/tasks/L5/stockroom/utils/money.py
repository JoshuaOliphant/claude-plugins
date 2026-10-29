"""Money is stored as integer cents; these helpers convert at the edges."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£", "CAD": "C$"}


def parse_money(raw: str | int | float | Decimal) -> int:
    """Parse ``"12.50"``, ``"$1,200"`` or a number into cents."""
    if isinstance(raw, int):
        return raw * 100
    text = str(raw).strip().replace(",", "")
    for symbol in _SYMBOLS.values():
        text = text.replace(symbol, "")
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"not a money amount: {raw!r}") from None
    cents = (value * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(cents)


def format_cents(cents: int, currency: str = "USD") -> str:
    symbol = _SYMBOLS.get(currency, "")
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(int(cents)), 100)
    text = f"{sign}{symbol}{whole:,}.{frac:02d}"
    if not symbol:
        text = f"{text} {currency}"
    return text


def weighted_average_cents(old_qty: int, old_cost: int, add_qty: int, add_cost: int) -> int:
    """Moving-average unit cost after adding ``add_qty`` units at ``add_cost``.

    Stock that was zero or negative carries no meaningful cost, so the new
    receipt's cost wins outright in that case.
    """
    if add_qty <= 0:
        return old_cost
    if old_qty <= 0:
        return add_cost
    total = Decimal(old_qty * old_cost + add_qty * add_cost)
    avg = total / Decimal(old_qty + add_qty)
    return int(avg.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def extend(qty: int, unit_cents: int) -> int:
    return int(qty) * int(unit_cents)
