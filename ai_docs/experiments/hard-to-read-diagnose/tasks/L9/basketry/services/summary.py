"""Assembly of the customer-facing :class:`OrderSummary`."""

from __future__ import annotations

from ..domain.order import Order
from ..domain.summary import Adjustment, OrderSummary
from .packing import PackingPlan
from .pricing import PricedOrder
from .shipping import ShippingQuote


class SummaryBuilder:
    """Collects the pieces of a summary for one order at a time."""

    def __init__(self) -> None:
        self._notes: list[str] = []
        self._adjustments: list[Adjustment] = []

    def reset(self) -> None:
        self._notes = []
        self._adjustments = []

    def add_note(self, note: str) -> None:
        if note and note not in self._notes:
            self._notes.append(note)

    def add_adjustments(self, adjustments: list[Adjustment]) -> None:
        self._adjustments.extend(adjustments)

    def build(
        self,
        order: Order,
        priced: PricedOrder,
        shipping: ShippingQuote,
        plan: PackingPlan,
        tax_cents: int,
    ) -> OrderSummary:
        adjustments = list(self._adjustments)
        total = priced.subtotal_cents + sum(a.amount_cents for a in adjustments) + shipping.cents + tax_cents
        if order.contact.email_opt_in:
            self.add_note(f"Order updates will be emailed to {order.contact.email}.")
        if not order.fulfillment.ships:
            self.add_note("Bring your order number to the counter to collect.")
        summary = OrderSummary(
            order_id=order.order_id,
            customer_id=order.customer.customer_id,
            customer_name=order.customer.name,
            channel=order.channel,
            currency=order.currency,
            placed_on=order.placed_on.isoformat() if order.placed_on else None,
            lines=list(priced.lines),
            subtotal_cents=priced.subtotal_cents,
            adjustments=adjustments,
            shipping_cents=shipping.cents,
            shipping_label=shipping.label,
            tax_cents=tax_cents,
            total_cents=total,
            packed_items=list(plan.labels),
            boxes=plan.boxes,
            notes=list(self._notes),
        )
        self.reset()
        return summary
