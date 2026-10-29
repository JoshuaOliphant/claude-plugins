"""Unit-of-measure handling.

Stock is kept in each-units. Suppliers ship and invoice in other units, so
receipts are converted on the way in:

* ``EA`` - each, the base unit
* ``DZ`` - dozen, always 12 each
* ``CS`` - case, ``pack_size`` each as configured on the product
"""

from __future__ import annotations

from stockroom.domain.errors import ValidationError

EACH = "EA"
DOZEN = "DZ"
CASE = "CS"

_ALIASES = {
    "EA": EACH,
    "EACH": EACH,
    "PC": EACH,
    "PCS": EACH,
    "DZ": DOZEN,
    "DOZ": DOZEN,
    "DOZEN": DOZEN,
    "CS": CASE,
    "CASE": CASE,
    "CTN": CASE,
}


def normalize_uom(raw: str | None) -> str:
    if raw is None or not raw.strip():
        return EACH
    key = raw.strip().upper()
    try:
        return _ALIASES[key]
    except KeyError:
        raise ValidationError(f"unknown unit of measure {raw!r}") from None


def factor(uom: str, pack_size: int) -> int:
    uom = normalize_uom(uom)
    if uom == EACH:
        return 1
    if uom == DOZEN:
        return 12
    if pack_size < 1:
        raise ValidationError(f"pack size must be positive, got {pack_size}")
    return pack_size


def to_each(qty: int, uom: str, pack_size: int) -> int:
    """Convert ``qty`` expressed in ``uom`` into each-units."""
    return int(qty) * factor(uom, pack_size)


def from_each(qty_each: int, uom: str, pack_size: int) -> tuple[int, int]:
    """Split an each-quantity into whole ``uom`` units plus loose eaches."""
    f = factor(uom, pack_size)
    whole, loose = divmod(int(qty_each), f)
    return whole, loose


def per_each_cost(cost_cents: int, uom: str, pack_size: int) -> int:
    """Cost of one each when ``cost_cents`` is quoted per ``uom``.

    Rounds half up so that a case of 3 at $10.00 costs 333 cents per each
    rather than drifting down on every receipt.
    """
    f = factor(uom, pack_size)
    whole, rest = divmod(int(cost_cents), f)
    if rest * 2 >= f:
        whole += 1
    return whole


def describe(qty_each: int, pack_size: int) -> str:
    """Human-friendly quantity, e.g. ``"2 CS + 3 EA"`` for cased products."""
    if pack_size <= 1:
        return f"{qty_each} EA"
    cases, loose = from_each(qty_each, CASE, pack_size)
    if cases and loose:
        return f"{cases} CS + {loose} EA"
    if cases:
        return f"{cases} CS"
    return f"{loose} EA"
