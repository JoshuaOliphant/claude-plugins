"""Turn a supplier's raw row into catalog-shaped fields."""

from __future__ import annotations

from stockline.domain.categories import CategoryTree
from stockline.domain.models import FeedRow, Supplier
from stockline.domain.money import MoneyParseError, parse_money
from stockline.domain.units import normalize_uom
from stockline.utils.text import clean_sku, collapse_ws, display_name


class ColumnMapper:
    """Pick the supplier's columns out of a raw feed row."""

    FIELDS = ("sku", "name", "supplier_part", "category", "uom", "pack_size", "cost")

    def __init__(self, supplier: Supplier):
        self.supplier = supplier
        missing = [f for f in ("name", "cost") if f not in supplier.columns]
        if missing:
            raise ValueError(f"supplier {supplier.code} has no column for {', '.join(missing)}")

    def check_header(self, raw: dict) -> list[str]:
        return [col for f, col in self.supplier.columns.items() if col not in raw]

    def __call__(self, line_no: int, raw: dict) -> FeedRow:
        row = FeedRow(line_no=line_no, raw=raw, supplier_code=self.supplier.code)
        values = {f: raw.get(self.supplier.columns.get(f, ""), "") for f in self.FIELDS}
        row.sku = str(values["sku"])
        row.name = str(values["name"])
        row.supplier_part = str(values["supplier_part"])
        row.category = str(values["category"])
        row.uom = str(values["uom"])
        row.raw_pack = values["pack_size"]
        row.raw_cost = values["cost"]
        return row


class Normalizer:
    def __init__(self, supplier: Supplier, categories: CategoryTree):
        self.supplier = supplier
        self.categories = categories

    def map_category(self, code: str) -> str:
        code = collapse_ws(code)
        mapped = self.supplier.category_map.get(code)
        if mapped is None:
            mapped = self.supplier.category_map.get(code.upper(), code.lower())
        return self.categories.resolve(mapped) or ""

    def __call__(self, row: FeedRow) -> FeedRow:
        row.sku = clean_sku(row.sku)
        row.supplier_part = collapse_ws(row.supplier_part).upper()
        row.name = display_name(row.name)
        row.category = self.map_category(row.category) if row.category else ""
        row.uom = normalize_uom(row.uom) or "EA"
        raw_pack = row.raw_pack
        try:
            row.pack_size = int(float(raw_pack)) if str(raw_pack).strip() else 1
        except ValueError:
            row.errors.append(f"bad pack size {raw_pack!r}")
        try:
            row.cost = parse_money(row.raw_cost)
        except MoneyParseError as exc:
            row.errors.append(f"bad cost: {exc}")
        return row
