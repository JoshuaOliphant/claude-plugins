"""Catalog products."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

TAX_CLASSES = frozenset({"general", "clothing", "food"})


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    category: str
    price_cents: int
    weight_grams: int
    giftable: bool = False
    tax_class: str = "general"

    def __post_init__(self) -> None:
        if self.price_cents < 0:
            raise ValueError(f"{self.sku}: price cannot be negative")
        if self.weight_grams < 0:
            raise ValueError(f"{self.sku}: weight cannot be negative")
        if self.tax_class not in TAX_CLASSES:
            raise ValueError(f"{self.sku}: unknown tax class {self.tax_class!r}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Product":
        return cls(
            sku=data["sku"],
            name=data["name"],
            category=data["category"],
            price_cents=int(data["price_cents"]),
            weight_grams=int(data["weight_grams"]),
            giftable=bool(data.get("giftable", False)),
            tax_class=data.get("tax_class", "general"),
        )
