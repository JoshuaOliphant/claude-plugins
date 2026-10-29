"""Import supplier receipts from a CSV file.

Expected header (case-insensitive, extra columns ignored)::

    sku,qty,uom,unit_cost,warehouse,reference,received_on

``uom``, ``unit_cost``, ``warehouse``, ``reference`` and ``received_on`` are
optional. Rows are validated up front; nothing is posted if any row is
invalid, so a half-imported file never has to be untangled by hand.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from stockroom.domain import units
from stockroom.domain.errors import StockroomError, ValidationError
from stockroom.services.inventory import InventoryService
from stockroom.utils.dates import parse_date
from stockroom.utils.money import parse_money

REQUIRED = ("sku", "qty")


@dataclass(frozen=True)
class ReceiptLine:
    row: int
    sku: str
    qty: int
    uom: str | None
    unit_cost_cents: int | None
    warehouse: str | None
    reference: str | None
    received_on: date | None


@dataclass
class ImportSummary:
    lines: int = 0
    units: int = 0
    skus: set[str] | None = None

    def __post_init__(self):
        if self.skus is None:
            self.skus = set()


def _blank(value: str | None) -> bool:
    return value is None or not value.strip()


def parse(path: Path) -> list[ReceiptLine]:
    errors: list[str] = []
    result: list[ReceiptLine] = []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValidationError(f"{path}: empty file")
        reader.fieldnames = [f.strip().lower() for f in reader.fieldnames]
        missing = [c for c in REQUIRED if c not in reader.fieldnames]
        if missing:
            raise ValidationError(f"{path}: missing column(s) {', '.join(missing)}")

        for rownum, raw in enumerate(reader, start=2):
            if all(_blank(v) for v in raw.values()):
                continue
            try:
                result.append(_line(rownum, raw))
            except (ValueError, StockroomError) as exc:
                errors.append(f"row {rownum}: {exc}")
    if errors:
        raise ValidationError(f"{path}: " + "; ".join(errors))
    return result


def _line(rownum: int, raw: dict[str, str]) -> ReceiptLine:
    sku = (raw.get("sku") or "").strip().upper()
    if not sku:
        raise ValueError("sku is required")
    qty_text = (raw.get("qty") or "").strip()
    if not qty_text.lstrip("-").isdigit():
        raise ValueError(f"qty {qty_text!r} is not a whole number")
    qty = int(qty_text)
    if qty <= 0:
        raise ValueError("qty must be positive")
    uom = None if _blank(raw.get("uom")) else units.normalize_uom(raw["uom"])
    cost = None if _blank(raw.get("unit_cost")) else parse_money(raw["unit_cost"])
    warehouse = None if _blank(raw.get("warehouse")) else raw["warehouse"].strip().upper()
    reference = None if _blank(raw.get("reference")) else raw["reference"].strip()
    received_on = None if _blank(raw.get("received_on")) else parse_date(raw["received_on"])
    return ReceiptLine(rownum, sku, qty, uom, cost, warehouse, reference, received_on)


def import_file(service: InventoryService, path: Path) -> ImportSummary:
    lines = parse(path)
    # Resolve every SKU and warehouse before posting anything.
    for line in lines:
        service.catalog.product(line.sku)
        if line.warehouse:
            service.catalog.warehouse(line.warehouse)

    summary = ImportSummary()
    for line in lines:
        level = service.receive(
            line.sku,
            line.qty,
            warehouse=line.warehouse,
            uom=line.uom,
            unit_cost_cents=line.unit_cost_cents,
            reference=line.reference,
            received_on=line.received_on,
        )
        product = service.catalog.product(line.sku)
        summary.lines += 1
        summary.units += units.to_each(line.qty, line.uom or product.uom, product.pack_size)
        summary.skus.add(level.sku)
    return summary
