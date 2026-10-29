"""Opening balances and on-hand snapshots stored as JSON."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Iterable

from stockflow.domain.catalog import Catalog
from stockflow.domain.errors import StockflowError
from stockflow.domain.models import StockLevel
from stockflow.utils.timeutil import iso, parse_date


class SnapshotError(StockflowError):
    pass


def load_opening_balances(path: Path, catalog: Catalog | None = None) -> list[StockLevel]:
    """Load the balances carried forward from the last stock count.

    Entries for SKUs that are not in the catalog are dropped: they belong to
    items that have since been delisted and would only clutter reports.
    """
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise SnapshotError(f"{path}: {exc}") from exc
    as_of = parse_date(data["as_of"]) if data.get("as_of") else None
    levels = []
    for warehouse, items in sorted(data.get("balances", {}).items()):
        for sku_code, qty in sorted(items.items()):
            if catalog is not None:
                sku = catalog.lookup(sku_code)
                if sku is None:
                    continue
                sku_code = sku.code
            levels.append(
                StockLevel(
                    warehouse=warehouse.upper(),
                    sku=sku_code,
                    on_hand=int(qty),
                    last_movement=as_of,
                )
            )
    return levels


def snapshot_payload(levels: Iterable[StockLevel], as_of: date | None) -> dict:
    balances: dict[str, dict[str, int]] = {}
    for level in levels:
        balances.setdefault(level.warehouse, {})[level.sku] = level.on_hand
    return {
        "as_of": iso(as_of),
        "balances": {wh: dict(sorted(items.items())) for wh, items in sorted(balances.items())},
    }


def write_snapshot(path: Path, levels: Iterable[StockLevel], as_of: date | None) -> None:
    payload = snapshot_payload(levels, as_of)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    tmp.replace(path)
