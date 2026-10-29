"""Build the on-hand report from the repository."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from stockflow.adapters.repository import InMemoryStockRepository
from stockflow.config.settings import Settings
from stockflow.domain.catalog import Catalog
from stockflow.domain.models import StockLevel
from stockflow.utils.timeutil import latest


@dataclass(frozen=True)
class ReportRow:
    warehouse: str
    sku: str
    description: str
    category: str
    on_hand: int
    received: int
    issued: int
    movements: int
    last_movement: Optional[date]
    status: str


@dataclass
class StockReport:
    rows: list[ReportRow] = field(default_factory=list)
    as_of: Optional[date] = None
    movement_count: int = 0

    @property
    def total_on_hand(self) -> int:
        return sum(r.on_hand for r in self.rows)

    @property
    def warehouses(self) -> list[str]:
        return sorted({r.warehouse for r in self.rows})

    def by_warehouse(self) -> dict[str, int]:
        totals: dict[str, int] = {}
        for r in self.rows:
            totals[r.warehouse] = totals.get(r.warehouse, 0) + r.on_hand
        return dict(sorted(totals.items()))

    def by_category(self) -> dict[str, int]:
        totals: dict[str, int] = {}
        for r in self.rows:
            totals[r.category] = totals.get(r.category, 0) + r.on_hand
        return dict(sorted(totals.items()))

    def flagged(self, status: str) -> list[ReportRow]:
        return [r for r in self.rows if r.status == status]


class ReportService:
    def __init__(self, repository: InMemoryStockRepository, catalog: Catalog,
                 settings: Settings) -> None:
        self.repository = repository
        self.catalog = catalog
        self.settings = settings

    def _status(self, level: StockLevel, reorder_point: int) -> str:
        if level.on_hand < 0:
            return "NEGATIVE"
        if level.on_hand == 0:
            return "OUT"
        if level.on_hand <= reorder_point + self.settings.low_stock_margin:
            return "LOW"
        return "OK"

    def build(self, warehouse: str | None = None) -> StockReport:
        levels = self.repository.levels()
        if warehouse:
            levels = [lvl for lvl in levels if lvl.warehouse == warehouse.upper()]
        rows = []
        for level in levels:
            sku = self.catalog.lookup(level.sku)
            description = sku.description if sku else ""
            category = sku.category if sku else "UNKNOWN"
            reorder = sku.reorder_point if sku else 0
            rows.append(
                ReportRow(
                    warehouse=level.warehouse,
                    sku=level.sku,
                    description=description,
                    category=category,
                    on_hand=level.on_hand,
                    received=level.received,
                    issued=level.issued,
                    movements=level.movement_count,
                    last_movement=level.last_movement,
                    status=self._status(level, reorder),
                )
            )
        return StockReport(
            rows=rows,
            as_of=latest(r.last_movement for r in rows),
            movement_count=sum(r.movements for r in rows),
        )
