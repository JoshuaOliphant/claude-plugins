"""Unit-of-measure conversion into each SKU's base unit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from stockflow.domain.errors import UnitError
from stockflow.domain.models import Sku
from stockflow.utils.memo import memoize_method

_ALIASES = {
    "EACH": "EA",
    "PC": "EA",
    "PCS": "EA",
    "UNIT": "EA",
    "CASE": "CS",
    "CTN": "CS",
    "PACK": "PK",
    "PALLET": "PL",
}


def normalise_uom(raw: str) -> str:
    code = raw.strip().upper()
    return _ALIASES.get(code, code)


class UnitTable:
    """Conversion factors from a unit of measure to eaches.

    Cases are special: when a SKU declares its own ``case_size`` that wins
    over the table's generic case factor.
    """

    def __init__(self, factors: Mapping[str, int]) -> None:
        cleaned = {}
        for code, factor in factors.items():
            factor = int(factor)
            if factor <= 0:
                raise UnitError(f"factor for {code} must be positive")
            cleaned[normalise_uom(code)] = factor
        if cleaned.get("EA") != 1:
            raise UnitError("unit table must define EA with factor 1")
        self._factors = cleaned

    @classmethod
    def from_file(cls, path: Path) -> "UnitTable":
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return cls(data["factors"])

    @property
    def codes(self) -> list[str]:
        return sorted(self._factors)

    @memoize_method
    def factor(self, uom: str, case_size: int | None = None) -> int:
        code = normalise_uom(uom)
        if code == "CS" and case_size:
            return case_size
        try:
            return self._factors[code]
        except KeyError:
            raise UnitError(f"unknown unit of measure {uom!r}") from None

    def to_base(self, quantity: int, uom: str, sku: Sku) -> int:
        if normalise_uom(uom) == normalise_uom(sku.base_uom):
            return quantity
        return quantity * self.factor(uom, sku.case_size)
