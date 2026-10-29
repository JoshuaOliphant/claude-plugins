"""Find the catalog product a feed row refers to.

Order of preference:

1. our SKU, when the supplier sends it;
2. the supplier's own part number (catches SKU renames on their side);
3. a fuzzy name match within the same supplier, only for rows that carry
   no SKU at all (some suppliers leave it blank for brand-new lines).
"""

from __future__ import annotations

from dataclasses import dataclass

from stockline.adapters.repositories import CatalogRepository
from stockline.domain.models import FeedRow, Product

NEW = "new"
BY_SKU = "sku"
BY_PART = "supplier_part"
BY_NAME = "name"
CONFLICT = "conflict"
UNMATCHED = "unmatched"


@dataclass(frozen=True)
class MatchResult:
    method: str
    product: Product | None = None
    detail: str = ""

    @property
    def is_new(self) -> bool:
        return self.method == NEW


class Matcher:
    def __init__(self, catalog: CatalogRepository, allow_name_match: bool = True,
                 fuzzy_threshold: float = 0.92):
        self.catalog = catalog
        self.allow_name_match = allow_name_match
        self.fuzzy_threshold = fuzzy_threshold
        self.stats: dict[str, int] = {}

    def _count(self, result: MatchResult) -> MatchResult:
        self.stats[result.method] = self.stats.get(result.method, 0) + 1
        return result

    def match(self, row: FeedRow) -> MatchResult:
        if row.sku:
            product = self.catalog.find_by_sku(row.sku)
            if product is not None:
                if product.supplier_code != row.supplier_code:
                    return self._count(MatchResult(
                        CONFLICT, product,
                        f"SKU {row.sku} belongs to supplier {product.supplier_code}",
                    ))
                return self._count(MatchResult(BY_SKU, product))
        if row.supplier_part:
            product = self.catalog.find_by_supplier_part(row.supplier_code, row.supplier_part)
            if product is not None:
                return self._count(MatchResult(BY_PART, product))
        if not row.sku:
            if self.allow_name_match and row.name:
                hits = self.catalog.search_name(row.name, row.supplier_code, self.fuzzy_threshold)
                if len(hits) == 1 or (len(hits) > 1 and hits[0][0] > hits[1][0]):
                    return self._count(MatchResult(BY_NAME, hits[0][1], f"score {hits[0][0]:.2f}"))
            return self._count(MatchResult(UNMATCHED, None, "no SKU and no matching product"))
        return self._count(MatchResult(NEW))
