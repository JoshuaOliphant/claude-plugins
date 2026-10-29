"""Sell-price calculation from ``data/pricing_rules.json``.

A rule applies to a category and all of its descendants; the most
specific rule wins field by field (a child rule that only sets ``markup``
inherits ``min_margin`` and ``ending`` from its ancestors).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from stockline.domain.categories import CategoryTree
from stockline.domain.money import apply_ending, quantize

_RULE_FIELDS = ("markup", "min_margin", "ending")


@dataclass(frozen=True)
class PriceRule:
    markup: Decimal
    min_margin: Decimal
    ending: str


@lru_cache(maxsize=8)
def load_rules(path: Path) -> tuple[dict, dict[str, dict]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    default = dict(raw["default"])
    default.setdefault("ending", raw.get("ending", ""))
    by_category = {}
    for rule in raw.get("rules", []):
        by_category[rule["category"]] = {k: rule[k] for k in _RULE_FIELDS if k in rule}
    return default, by_category


class PriceCalculator:
    def __init__(self, rules_path: Path, categories: CategoryTree):
        self.rules_path = Path(rules_path)
        self.categories = categories

    def rule_for(self, category: str) -> PriceRule:
        default, by_category = load_rules(self.rules_path)
        merged: dict = {}
        for code in self.categories.lineage(category) if category else []:
            for k, v in by_category.get(code, {}).items():
                merged.setdefault(k, v)
        for k in _RULE_FIELDS:
            merged.setdefault(k, default.get(k, ""))
        return PriceRule(
            markup=Decimal(str(merged["markup"])),
            min_margin=Decimal(str(merged["min_margin"])),
            ending=str(merged["ending"]),
        )

    def price_for(self, category: str, cost: Decimal) -> Decimal:
        rule = self.rule_for(category)
        price = cost * (1 + rule.markup)
        if rule.min_margin < 1:
            floor = cost / (1 - rule.min_margin)
            if price < floor:
                price = floor
        return apply_ending(quantize(price), rule.ending)

    def __call__(self, row):
        if row.cost is not None and row.ok:
            row.price = self.price_for(row.category, row.cost)
        return row
