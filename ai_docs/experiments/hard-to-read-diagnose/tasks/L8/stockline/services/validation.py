"""Row-level validation rules."""

from __future__ import annotations

from decimal import Decimal

from stockline.domain.categories import CategoryTree
from stockline.domain.models import FeedRow
from stockline.domain.units import ALLOWED_UOMS

MAX_NAME = 120
MAX_COST = Decimal("250000")


class Validator:
    def __init__(self, categories: CategoryTree, require_category: bool = True):
        self.categories = categories
        self.require_category = require_category

    def __call__(self, row: FeedRow) -> FeedRow:
        errors = row.errors
        if not row.sku and not row.supplier_part:
            errors.append("row has neither SKU nor supplier part number")
        if row.sku and len(row.sku) > 32:
            errors.append(f"SKU too long ({len(row.sku)} chars)")
        if not row.name:
            errors.append("missing name")
        elif len(row.name) > MAX_NAME:
            row.name = row.name[:MAX_NAME].rstrip()
        if row.uom not in ALLOWED_UOMS:
            errors.append(f"unknown unit {row.uom!r}")
        if row.pack_size < 1:
            errors.append(f"pack size must be positive, got {row.pack_size}")
        if row.cost is not None:
            if row.cost <= 0:
                errors.append(f"cost must be positive, got {row.cost}")
            elif row.cost > MAX_COST:
                errors.append(f"cost {row.cost} above sanity limit")
        if self.require_category and not row.category:
            errors.append("unmapped category")
        elif row.category and row.category not in self.categories:
            errors.append(f"unknown category {row.category!r}")
        return row
