"""Units of measure."""

from __future__ import annotations

from decimal import Decimal

ALLOWED_UOMS = ["EA", "BX", "CS", "PK", "RL", "DZ", "GAL", "LB"]

_ALIASES = {
    "EACH": "EA",
    "PC": "EA",
    "PCS": "EA",
    "PIECE": "EA",
    "BOX": "BX",
    "CASE": "CS",
    "CT": "CS",
    "PACK": "PK",
    "PKG": "PK",
    "ROLL": "RL",
    "DOZ": "DZ",
    "DOZEN": "DZ",
    "GALLON": "GAL",
    "LBS": "LB",
}

# Units that always imply a fixed count regardless of the feed's pack column.
_FIXED_COUNTS = {"DZ": 12}


def normalize_uom(value: str) -> str:
    text = (value or "").strip().upper().rstrip(".")
    return _ALIASES.get(text, text)


def effective_pack(uom: str, pack_size: int) -> int:
    return _FIXED_COUNTS.get(uom, max(pack_size, 1))


def each_cost(cost: Decimal, uom: str, pack_size: int) -> Decimal:
    """Cost of a single piece, used for display and margin reports."""
    pieces = effective_pack(uom, pack_size)
    return (cost / pieces).quantize(Decimal("0.0001"))
