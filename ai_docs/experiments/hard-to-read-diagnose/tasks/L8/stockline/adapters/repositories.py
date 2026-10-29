"""Repositories over the key/value store."""

from __future__ import annotations

from typing import Iterable, Iterator

from stockline.adapters.repository_base import IndexedRepository
from stockline.adapters.store import MemoryStore
from stockline.domain.models import Change, ImportRun, Product, Supplier
from stockline.utils.text import similarity


def _sku_key(rec: dict) -> str | None:
    sku = rec.get("sku")
    return sku.upper() if sku else None


def _supplier_part_key(rec: dict) -> str | None:
    part = rec.get("supplier_part")
    if not part:
        return None
    return f"{rec.get('supplier_code', '')}:{part.upper()}"


class Sequences:
    """Monotonic counters kept in the ``meta`` namespace."""

    namespace = "meta"

    def __init__(self, store: MemoryStore):
        self._store = store

    def next(self, name: str) -> int:
        key = f"seq.{name}"
        rec = self._store.get(self.namespace, key) or {"value": 0}
        value = int(rec["value"]) + 1
        self._store.put(self.namespace, key, {"value": value})
        return value

    def current(self, name: str) -> int:
        rec = self._store.get(self.namespace, f"seq.{name}")
        return int(rec["value"]) if rec else 0


class CatalogRepository(IndexedRepository):
    namespace = "products"
    indexes = {"sku": _sku_key, "supplier_part": _supplier_part_key}

    def __init__(self, store: MemoryStore, sequences: Sequences | None = None):
        super().__init__(store)
        self._sequences = sequences or Sequences(store)

    def new_id(self) -> str:
        return f"P{self._sequences.next('product'):07d}"

    def get(self, product_id: str) -> Product | None:
        rec = self._get(product_id)
        return Product.from_record(rec) if rec else None

    def find_by_sku(self, sku: str) -> Product | None:
        rec = self._lookup("sku", sku.upper())
        return Product.from_record(rec) if rec else None

    def find_by_supplier_part(self, supplier_code: str, part: str) -> Product | None:
        rec = self._lookup("supplier_part", f"{supplier_code}:{part.upper()}")
        return Product.from_record(rec) if rec else None

    def save(self, product: Product) -> None:
        self._put(product.product_id, product.to_record())

    def delete(self, product_id: str) -> bool:
        return self._remove(product_id)

    def all(self) -> Iterator[Product]:
        for _, rec in self._scan():
            yield Product.from_record(rec)

    def by_supplier(self, supplier_code: str) -> list[Product]:
        return [p for p in self.all() if p.supplier_code == supplier_code]

    def search_name(self, text: str, supplier_code: str | None = None,
                    threshold: float = 0.85) -> list[tuple[float, Product]]:
        hits = []
        for product in self.all():
            if supplier_code and product.supplier_code != supplier_code:
                continue
            score = similarity(text, product.name)
            if score >= threshold:
                hits.append((score, product))
        hits.sort(key=lambda h: (-h[0], h[1].sku))
        return hits


class SupplierRepository(IndexedRepository):
    namespace = "suppliers"
    indexes = {"prefix": lambda rec: rec.get("filename_prefix", "").lower() or None}

    def get(self, code: str) -> Supplier | None:
        rec = self._get(code.upper())
        return Supplier.from_record(rec) if rec else None

    def by_prefix(self, prefix: str) -> Supplier | None:
        rec = self._lookup("prefix", prefix.lower())
        return Supplier.from_record(rec) if rec else None

    def save(self, supplier: Supplier) -> None:
        self._put(supplier.code.upper(), supplier.to_record())

    def all(self) -> list[Supplier]:
        return sorted((Supplier.from_record(r) for _, r in self._scan()), key=lambda s: s.code)

    def ensure(self, suppliers: Iterable[Supplier]) -> int:
        """Insert suppliers that are not stored yet; returns how many were added."""
        added = 0
        for supplier in suppliers:
            if self._get(supplier.code.upper()) is None:
                self.save(supplier)
                added += 1
        return added


class JournalRepository:
    """Append-only change log."""

    namespace = "journal"

    def __init__(self, store: MemoryStore, sequences: Sequences | None = None):
        self._store = store
        self._sequences = sequences or Sequences(store)

    def append(self, change: Change) -> Change:
        change.seq = self._sequences.next("journal")
        self._store.put(self.namespace, f"{change.seq:010d}", change.to_record())
        return change

    def entries(self) -> Iterator[Change]:
        for key in sorted(self._store.keys(self.namespace)):
            rec = self._store.get(self.namespace, key)
            if rec is not None:
                yield Change.from_record(rec)

    def for_sku(self, sku: str) -> list[Change]:
        sku = sku.upper()
        return [c for c in self.entries() if c.sku.upper() == sku]

    def for_run(self, run_id: str) -> list[Change]:
        return [c for c in self.entries() if c.run_id == run_id]

    def __len__(self) -> int:
        return self._store.count(self.namespace)


class RunRepository:
    namespace = "runs"

    def __init__(self, store: MemoryStore):
        self._store = store

    def save(self, run: ImportRun) -> None:
        self._store.put(self.namespace, run.run_id, run.to_record())

    def get(self, run_id: str) -> ImportRun | None:
        rec = self._store.get(self.namespace, run_id)
        return ImportRun.from_record(rec) if rec else None

    def all(self) -> list[ImportRun]:
        runs = [ImportRun.from_record(r) for _, r in self._store.scan(self.namespace)]
        runs.sort(key=lambda r: (r.started_at, r.run_id))
        return runs

    def latest(self, supplier_code: str | None = None) -> ImportRun | None:
        runs = [r for r in self.all() if supplier_code is None or r.supplier_code == supplier_code]
        return runs[-1] if runs else None
