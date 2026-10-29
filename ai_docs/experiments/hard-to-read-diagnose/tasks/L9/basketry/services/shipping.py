"""Shipping quotes."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import Settings
from ..domain.order import Order


@dataclass(frozen=True)
class ShippingQuote:
    cents: int
    label: str


class ShippingQuoter:
    def __init__(self, settings: Settings):
        self.settings = settings

    def quote(self, order: Order, discounted_subtotal_cents: int, shipped_grams: int) -> ShippingQuote:
        fulfillment = order.fulfillment
        if not fulfillment.ships:
            return ShippingQuote(0, "Store pickup")
        speed = fulfillment.speed
        label = f"Shipping ({speed})"
        if speed == "standard" and discounted_subtotal_cents >= self.settings.free_shipping_over_cents:
            return ShippingQuote(0, label + " - free")
        rate = self.settings.shipping_rate(speed)
        kilos = -(-shipped_grams // 1000)
        return ShippingQuote(rate.base_cents + rate.per_kg_cents * kilos, label)
