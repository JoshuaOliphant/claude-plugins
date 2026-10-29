"""Core value objects for stock movements and balances."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


class MovementKind(enum.Enum):
    RECEIPT = "RECEIPT"
    SHIPMENT = "SHIPMENT"
    ADJUSTMENT = "ADJUSTMENT"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    RETURN = "RETURN"

    @property
    def sign(self) -> int:
        """Direction in which a positive quantity moves the on-hand balance."""
        if self in (MovementKind.SHIPMENT, MovementKind.TRANSFER_OUT):
            return -1
        return 1

    @property
    def allows_negative_quantity(self) -> bool:
        return self is MovementKind.ADJUSTMENT

    @classmethod
    def parse(cls, raw: str) -> "MovementKind":
        key = raw.strip().upper().replace("-", "_").replace(" ", "_")
        key = _KIND_ALIASES.get(key, key)
        try:
            return cls(key)
        except ValueError:
            raise ValueError(f"unknown movement kind {raw!r}") from None


_KIND_ALIASES = {
    "RCV": "RECEIPT",
    "RECV": "RECEIPT",
    "GR": "RECEIPT",
    "SHIP": "SHIPMENT",
    "GI": "SHIPMENT",
    "ADJ": "ADJUSTMENT",
    "COUNT": "ADJUSTMENT",
    "XFER_IN": "TRANSFER_IN",
    "XFER_OUT": "TRANSFER_OUT",
    "RMA": "RETURN",
}


@dataclass(frozen=True)
class Sku:
    code: str
    description: str
    category: str
    base_uom: str = "EA"
    case_size: Optional[int] = None
    reorder_point: int = 0
    barcodes: tuple[str, ...] = ()
    active: bool = True


@dataclass(frozen=True)
class Movement:
    """A validated stock movement expressed in base units."""

    movement_id: str
    reference: str
    warehouse: str
    sku: str
    kind: MovementKind
    quantity: int
    occurred_on: date
    source: str = ""

    @property
    def signed_quantity(self) -> int:
        return self.kind.sign * self.quantity

    @property
    def dedup_key(self) -> tuple[str, str, str]:
        return (self.warehouse, self.reference, self.sku)


@dataclass
class StockLevel:
    """Running on-hand balance for one SKU in one warehouse."""

    warehouse: str
    sku: str
    on_hand: int = 0
    movement_count: int = 0
    last_movement: Optional[date] = None
    received: int = 0
    issued: int = 0

    def apply(self, movement: Movement) -> None:
        delta = movement.signed_quantity
        self.on_hand += delta
        self.movement_count += 1
        if delta >= 0:
            self.received += delta
        else:
            self.issued += -delta
        if self.last_movement is None or movement.occurred_on > self.last_movement:
            self.last_movement = movement.occurred_on

    def copy(self) -> "StockLevel":
        return StockLevel(
            warehouse=self.warehouse,
            sku=self.sku,
            on_hand=self.on_hand,
            movement_count=self.movement_count,
            last_movement=self.last_movement,
            received=self.received,
            issued=self.issued,
        )


@dataclass(frozen=True)
class RawRow:
    source: str
    line_no: int
    fields: dict


@dataclass
class IngestResult:
    source: str
    rows_read: int = 0
    posted: int = 0
    rejected: int = 0
    duplicates: int = 0
    errors: list[str] = field(default_factory=list)

    def merge(self, other: "IngestResult") -> None:
        self.rows_read += other.rows_read
        self.posted += other.posted
        self.rejected += other.rejected
        self.duplicates += other.duplicates
        self.errors.extend(other.errors)
