"""Packing plans: how many boxes, and what goes in them besides the goods.

The planner annotates the order's fulfillment with warehouse inserts: one
gift-wrap instruction per gift line, a printed card for a gift message and a
free sample on qualifying orders.  Store pickups are bagged at the counter,
so they get inserts but no boxes.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..adapters.catalog import Catalog
from ..config import Settings
from ..domain.order import Order


@dataclass(frozen=True)
class PackingPlan:
    boxes: int
    shipped_grams: int
    labels: tuple[str, ...]


class PackingPlanner:
    def __init__(self, settings: Settings, catalog: Catalog):
        self.settings = settings
        self.catalog = catalog

    def plan(self, order: Order, discounted_subtotal_cents: int) -> PackingPlan:
        fulfillment = order.fulfillment
        inserts = fulfillment.inserts

        for line in order.gift_lines():
            inserts.append({"kind": "gift_wrap", "label": f"Gift wrap: {line.name}", "sku": line.sku})
        if fulfillment.gift_note:
            inserts.append({"kind": "gift_card", "label": f"Gift message card: \"{fulfillment.gift_note}\""})
        if discounted_subtotal_cents >= self.settings.sample_threshold_cents and not fulfillment.has_insert("sample"):
            sample = self.catalog.get(self.settings.sample_sku)
            inserts.append({"kind": "sample", "label": f"Free sample: {sample.name}", "sku": sample.sku})

        if not fulfillment.ships:
            return PackingPlan(boxes=0, shipped_grams=0, labels=tuple(i["label"] for i in inserts))

        boxes = self._box_count(order)
        shipped = order.weight_grams + boxes * self.settings.box_tare_grams
        return PackingPlan(boxes=boxes, shipped_grams=shipped, labels=tuple(i["label"] for i in inserts))

    def _box_count(self, order: Order) -> int:
        capacity = self.settings.box_capacity_grams
        boxes: list[int] = []
        items = sorted(
            (line.weight_grams for line in order.lines for _ in range(line.quantity)),
            reverse=True,
        )
        for grams in items:
            for i, used in enumerate(boxes):
                if used + grams <= capacity:
                    boxes[i] = used + grams
                    break
            else:
                boxes.append(grams)
        return max(len(boxes), 1)
