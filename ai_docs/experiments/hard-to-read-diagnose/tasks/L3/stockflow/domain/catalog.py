"""The SKU master: what may be stocked and how it is described."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Iterator, Optional

from stockflow.domain.errors import CatalogError
from stockflow.domain.models import Sku
from stockflow.utils.memo import LazyValue


class Catalog:
    def __init__(self, skus: Iterable[Sku]) -> None:
        self._skus: dict[str, Sku] = {}
        for sku in skus:
            code = sku.code.upper()
            if code in self._skus:
                raise CatalogError(f"duplicate SKU {code}")
            self._skus[code] = sku
        self._barcodes = LazyValue(self._build_barcode_index)

    @classmethod
    def from_file(cls, path: Path) -> "Catalog":
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            raise CatalogError(f"cannot load catalog {path}: {exc}") from exc
        skus = []
        for entry in data.get("skus", []):
            try:
                skus.append(
                    Sku(
                        code=entry["code"].upper(),
                        description=entry.get("description", ""),
                        category=entry.get("category", "GENERAL"),
                        base_uom=entry.get("base_uom", "EA"),
                        case_size=entry.get("case_size"),
                        reorder_point=int(entry.get("reorder_point", 0)),
                        barcodes=tuple(entry.get("barcodes", ())),
                        active=bool(entry.get("active", True)),
                    )
                )
            except KeyError as exc:
                raise CatalogError(f"catalog entry missing {exc}") from exc
        return cls(skus)

    def _build_barcode_index(self) -> dict[str, str]:
        index = {}
        for sku in self._skus.values():
            for code in sku.barcodes:
                index[code] = sku.code
        return index

    def __len__(self) -> int:
        return len(self._skus)

    def __iter__(self) -> Iterator[Sku]:
        return iter(sorted(self._skus.values(), key=lambda s: s.code))

    def __contains__(self, code: str) -> bool:
        return self.lookup(code) is not None

    def get(self, code: str) -> Sku:
        sku = self.lookup(code)
        if sku is None:
            raise KeyError(code)
        return sku

    def lookup(self, code: str) -> Optional[Sku]:
        key = code.strip().upper()
        sku = self._skus.get(key)
        if sku is not None:
            return sku
        alias = self._barcodes.get().get(code.strip())
        if alias is not None:
            return self._skus[alias]
        return None

    def categories(self) -> list[str]:
        return sorted({s.category for s in self._skus.values()})
