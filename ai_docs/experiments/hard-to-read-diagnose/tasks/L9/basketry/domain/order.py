"""Orders as seen by the pricing and packing services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .customer import Customer

FULFILLMENT_METHODS = ("ship", "pickup")
SHIPPING_SPEEDS = ("standard", "express")
INSERT_KINDS = ("gift_wrap", "gift_card", "sample", "flyer", "note")


@dataclass(frozen=True)
class OrderLine:
    sku: str
    name: str
    category: str
    quantity: int
    unit_price_cents: int
    weight_grams: int
    tax_class: str = "general"
    gift: bool = False

    @property
    def total_cents(self) -> int:
        return self.unit_price_cents * self.quantity

    @property
    def total_weight_grams(self) -> int:
        return self.weight_grams * self.quantity


@dataclass
class Contact:
    email: str | None = None
    email_opt_in: bool = False
    sms_opt_in: bool = False


@dataclass
class Fulfillment:
    """How the order leaves the warehouse.

    ``inserts`` are the warehouse insert instructions (gift wrap, cards,
    samples, flyers).  They are plain dicts with ``kind`` and ``label`` keys
    because they are handed to the warehouse system unchanged.
    """

    method: str = "ship"
    speed: str = "standard"
    gift_note: str | None = None
    inserts: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.method not in FULFILLMENT_METHODS:
            raise ValueError(f"unknown fulfillment method {self.method!r}")
        if self.speed not in SHIPPING_SPEEDS:
            raise ValueError(f"unknown shipping speed {self.speed!r}")
        if not isinstance(self.inserts, list):
            raise ValueError("inserts must be a list")
        for insert in self.inserts:
            if not isinstance(insert, dict) or insert.get("kind") not in INSERT_KINDS:
                raise ValueError(f"invalid insert {insert!r}")
            if not isinstance(insert.get("label"), str):
                raise ValueError(f"insert {insert!r} is missing a label")

    @property
    def ships(self) -> bool:
        return self.method == "ship"

    def has_insert(self, kind: str) -> bool:
        return any(insert["kind"] == kind for insert in self.inserts)


@dataclass
class Order:
    order_id: str
    customer: Customer
    channel: str
    currency: str
    lines: list[OrderLine] = field(default_factory=list)
    fulfillment: Fulfillment = field(default_factory=Fulfillment)
    contact: Contact = field(default_factory=Contact)
    coupons: tuple[str, ...] = ()
    placed_on: date | None = None

    @property
    def item_count(self) -> int:
        return sum(line.quantity for line in self.lines)

    @property
    def merchandise_cents(self) -> int:
        return sum(line.total_cents for line in self.lines)

    @property
    def weight_grams(self) -> int:
        return sum(line.total_weight_grams for line in self.lines)

    def gift_lines(self) -> list[OrderLine]:
        return [line for line in self.lines if line.gift]

    def lines_in(self, category: str) -> list[OrderLine]:
        return [line for line in self.lines if line.category == category]
