"""Turn raw CSV rows into validated movements."""

from __future__ import annotations

from datetime import date

from stockflow.config.settings import Settings
from stockflow.domain.catalog import Catalog
from stockflow.domain.errors import UnitError, ValidationError
from stockflow.domain.models import Movement, MovementKind, RawRow
from stockflow.domain.units import UnitTable, normalise_uom
from stockflow.utils.ids import movement_id
from stockflow.utils.timeutil import parse_date

EARLIEST_DATE = date(2000, 1, 1)


class RowValidator:
    def __init__(self, catalog: Catalog, units: UnitTable, settings: Settings) -> None:
        self.catalog = catalog
        self.units = units
        self.settings = settings

    def _fail(self, row: RawRow, reason: str) -> ValidationError:
        return ValidationError(row.source, row.line_no, reason)

    def _quantity(self, row: RawRow, kind: MovementKind) -> int:
        raw = row.fields.get("quantity", "").replace(",", "").strip()
        if not raw:
            raise self._fail(row, "quantity is empty")
        try:
            if "." in raw:
                value = float(raw)
                if not value.is_integer():
                    raise self._fail(row, f"fractional quantity {raw}")
                qty = int(value)
            else:
                qty = int(raw)
        except ValueError:
            raise self._fail(row, f"quantity {raw!r} is not a number") from None
        if qty == 0:
            raise self._fail(row, "quantity is zero")
        if qty < 0 and not kind.allows_negative_quantity:
            raise self._fail(row, f"negative quantity not allowed for {kind.value}")
        return qty

    def _warehouse(self, row: RawRow) -> str:
        warehouse = row.fields.get("warehouse", "").strip().upper()
        if not warehouse:
            raise self._fail(row, "warehouse is empty")
        known = self.settings.warehouses
        if known and warehouse not in known:
            raise self._fail(row, f"unknown warehouse {warehouse}")
        return warehouse

    def validate(self, row: RawRow) -> Movement:
        f = row.fields
        try:
            kind = MovementKind.parse(f.get("kind", ""))
        except ValueError as exc:
            raise self._fail(row, str(exc)) from None

        warehouse = self._warehouse(row)

        sku = self.catalog.lookup(f.get("sku", ""))
        if sku is None:
            raise self._fail(row, f"unknown SKU {f.get('sku', '')!r}")
        if not sku.active and not self.settings.allow_inactive_skus:
            raise self._fail(row, f"SKU {sku.code} is inactive")

        try:
            occurred = parse_date(f.get("date", ""))
        except ValueError as exc:
            raise self._fail(row, str(exc)) from None
        if occurred < EARLIEST_DATE:
            raise self._fail(row, f"date {occurred} is before {EARLIEST_DATE}")

        qty = self._quantity(row, kind)
        uom = normalise_uom(f.get("uom") or sku.base_uom)
        try:
            base_qty = self.units.to_base(qty, uom, sku)
        except UnitError as exc:
            raise self._fail(row, str(exc)) from None

        reference = f.get("reference", "").strip()
        if not reference:
            raise self._fail(row, "reference is empty")

        return Movement(
            movement_id=movement_id(warehouse, reference, sku.code),
            reference=reference,
            warehouse=warehouse,
            sku=sku.code,
            kind=kind,
            quantity=base_qty,
            occurred_on=occurred,
            source=f"{row.source}:{row.line_no}",
        )
