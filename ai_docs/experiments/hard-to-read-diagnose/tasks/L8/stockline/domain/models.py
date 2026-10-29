"""Core domain records.

Records are converted to and from plain dicts so that the storage layer
only ever deals in JSON-compatible values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

TRACKED_FIELDS = (
    "name",
    "supplier_part",
    "category",
    "uom",
    "pack_size",
    "cost",
    "price",
    "status",
)

ACTIVE = "active"
DISCONTINUED = "discontinued"


@dataclass
class Product:
    product_id: str
    sku: str
    name: str
    supplier_code: str
    supplier_part: str = ""
    category: str = ""
    uom: str = "EA"
    pack_size: int = 1
    cost: Decimal = Decimal("0")
    price: Decimal = Decimal("0")
    status: str = ACTIVE
    created_at: str = ""
    updated_at: str = ""

    def to_record(self) -> dict:
        return {
            "product_id": self.product_id,
            "sku": self.sku,
            "name": self.name,
            "supplier_code": self.supplier_code,
            "supplier_part": self.supplier_part,
            "category": self.category,
            "uom": self.uom,
            "pack_size": self.pack_size,
            "cost": str(self.cost),
            "price": str(self.price),
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_record(cls, rec: dict) -> "Product":
        return cls(
            product_id=rec["product_id"],
            sku=rec["sku"],
            name=rec.get("name", ""),
            supplier_code=rec.get("supplier_code", ""),
            supplier_part=rec.get("supplier_part", ""),
            category=rec.get("category", ""),
            uom=rec.get("uom", "EA"),
            pack_size=int(rec.get("pack_size", 1)),
            cost=Decimal(rec.get("cost", "0")),
            price=Decimal(rec.get("price", "0")),
            status=rec.get("status", ACTIVE),
            created_at=rec.get("created_at", ""),
            updated_at=rec.get("updated_at", ""),
        )

    def diff(self, other: "Product") -> dict[str, tuple]:
        """Return ``{field: (before, after)}`` for tracked fields that differ."""
        changes = {}
        for name in TRACKED_FIELDS:
            before, after = getattr(self, name), getattr(other, name)
            if before != after:
                changes[name] = (before, after)
        return changes

    @property
    def margin(self) -> Decimal:
        if not self.price:
            return Decimal("0")
        return ((self.price - self.cost) / self.price).quantize(Decimal("0.001"))


@dataclass(frozen=True)
class Supplier:
    code: str
    name: str
    feed_format: str
    filename_prefix: str
    columns: dict
    category_map: dict
    active: bool = True

    def to_record(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "feed_format": self.feed_format,
            "filename_prefix": self.filename_prefix,
            "columns": dict(self.columns),
            "category_map": dict(self.category_map),
            "active": self.active,
        }

    @classmethod
    def from_record(cls, rec: dict) -> "Supplier":
        return cls(
            code=rec["code"],
            name=rec.get("name", rec["code"]),
            feed_format=rec.get("feed_format", "csv"),
            filename_prefix=rec.get("filename_prefix", rec["code"].lower()),
            columns=dict(rec.get("columns", {})),
            category_map=dict(rec.get("category_map", {})),
            active=bool(rec.get("active", True)),
        )


@dataclass
class FeedRow:
    """One feed line on its way through the pipeline."""

    line_no: int
    raw: dict
    supplier_code: str = ""
    sku: str = ""
    name: str = ""
    supplier_part: str = ""
    category: str = ""
    uom: str = ""
    pack_size: int = 1
    cost: Decimal | None = None
    price: Decimal | None = None
    raw_pack: object = ""
    raw_cost: object = None
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def identity(self) -> tuple[str, str]:
        return (self.sku, self.supplier_part)


@dataclass
class Change:
    seq: int
    at: str
    run_id: str
    product_id: str
    sku: str
    kind: str
    fields: dict

    def to_record(self) -> dict:
        return {
            "seq": self.seq,
            "at": self.at,
            "run_id": self.run_id,
            "product_id": self.product_id,
            "sku": self.sku,
            "kind": self.kind,
            "fields": self.fields,
        }

    @classmethod
    def from_record(cls, rec: dict) -> "Change":
        return cls(**{k: rec[k] for k in ("seq", "at", "run_id", "product_id", "sku", "kind", "fields")})


@dataclass
class ImportRun:
    run_id: str
    supplier_code: str
    source: str
    started_at: str
    finished_at: str = ""
    status: str = "running"
    rows_seen: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    rejected: int = 0
    duplicates: int = 0
    discontinued: int = 0

    COUNTERS = ("rows_seen", "created", "updated", "unchanged", "rejected", "duplicates", "discontinued")

    def to_record(self) -> dict:
        rec = {
            "run_id": self.run_id,
            "supplier_code": self.supplier_code,
            "source": self.source,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status,
        }
        for name in self.COUNTERS:
            rec[name] = getattr(self, name)
        return rec

    @classmethod
    def from_record(cls, rec: dict) -> "ImportRun":
        run = cls(
            run_id=rec["run_id"],
            supplier_code=rec["supplier_code"],
            source=rec.get("source", ""),
            started_at=rec.get("started_at", ""),
            finished_at=rec.get("finished_at", ""),
            status=rec.get("status", "running"),
        )
        for name in cls.COUNTERS:
            setattr(run, name, int(rec.get(name, 0)))
        return run
