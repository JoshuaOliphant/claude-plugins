"""Read-only product catalog backed by ``catalog.json``."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from ..domain.product import Product


class UnknownProduct(LookupError):
    def __init__(self, sku: str):
        super().__init__(f"unknown product {sku!r}")
        self.sku = sku


class Catalog:
    """Product lookup by SKU.

    Catalog files are parsed once per process and the parsed products are
    shared by every ``Catalog`` pointed at the same file.  Products are frozen
    dataclasses, so sharing them is safe.
    """

    _parsed: dict[Path, dict[str, Product]] = {}

    def __init__(self, path: Path):
        self.path = Path(path).resolve()
        self._products = self._load(self.path)

    @classmethod
    def _load(cls, path: Path) -> dict[str, Product]:
        if path not in cls._parsed:
            with path.open(encoding="utf-8") as fh:
                raw = json.load(fh)
            products: dict[str, Product] = {}
            for entry in raw["products"]:
                product = Product.from_dict(entry)
                if product.sku in products:
                    raise ValueError(f"duplicate SKU {product.sku} in {path}")
                products[product.sku] = product
            cls._parsed[path] = products
        return cls._parsed[path]

    @classmethod
    def clear_cache(cls) -> None:
        cls._parsed.clear()

    def get(self, sku: str) -> Product:
        try:
            return self._products[sku]
        except KeyError:
            raise UnknownProduct(sku) from None

    def __contains__(self, sku: object) -> bool:
        return sku in self._products

    def __iter__(self) -> Iterator[Product]:
        return iter(sorted(self._products.values(), key=lambda p: (p.category, p.sku)))

    def __len__(self) -> int:
        return len(self._products)

    def categories(self) -> list[str]:
        return sorted({p.category for p in self._products.values()})

    def in_category(self, category: str) -> list[Product]:
        return [p for p in self if p.category == category]
