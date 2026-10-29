"""The customer-facing order summary."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SummaryLine:
    sku: str
    name: str
    quantity: int
    unit_price_cents: int
    total_cents: int
    gift: bool = False


@dataclass(frozen=True)
class Adjustment:
    """A discount (negative) or fee (positive) applied to the order."""

    code: str
    description: str
    amount_cents: int


@dataclass
class OrderSummary:
    order_id: str
    customer_id: str
    customer_name: str
    channel: str
    currency: str
    placed_on: str | None
    lines: list[SummaryLine] = field(default_factory=list)
    subtotal_cents: int = 0
    adjustments: list[Adjustment] = field(default_factory=list)
    shipping_cents: int = 0
    shipping_label: str = ""
    tax_cents: int = 0
    total_cents: int = 0
    packed_items: list[str] = field(default_factory=list)
    boxes: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def discount_cents(self) -> int:
        return sum(a.amount_cents for a in self.adjustments if a.amount_cents < 0)

    @property
    def fee_cents(self) -> int:
        return sum(a.amount_cents for a in self.adjustments if a.amount_cents > 0)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["discount_cents"] = self.discount_cents
        data["fee_cents"] = self.fee_cents
        return data
