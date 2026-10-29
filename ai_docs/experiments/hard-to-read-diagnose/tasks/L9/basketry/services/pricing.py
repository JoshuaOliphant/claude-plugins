"""Line pricing and order-level fees."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import Settings
from ..domain.order import Order
from ..domain.summary import Adjustment, SummaryLine


@dataclass(frozen=True)
class PricedOrder:
    lines: tuple[SummaryLine, ...]
    subtotal_cents: int

    def category_subtotal(self, order: Order, categories: set[str]) -> int:
        wanted = {line.sku for line in order.lines if line.category in categories}
        return sum(line.total_cents for line in self.lines if line.sku in wanted)


class Pricer:
    def __init__(self, settings: Settings):
        self.settings = settings

    def price(self, order: Order) -> PricedOrder:
        lines = tuple(
            SummaryLine(
                sku=line.sku,
                name=line.name,
                quantity=line.quantity,
                unit_price_cents=line.unit_price_cents,
                total_cents=line.total_cents,
                gift=line.gift,
            )
            for line in order.lines
        )
        return PricedOrder(lines=lines, subtotal_cents=sum(line.total_cents for line in lines))

    def fees(self, order: Order) -> list[Adjustment]:
        fees: list[Adjustment] = []
        wrapped = sum(line.quantity for line in order.gift_lines())
        if wrapped:
            fee = self.settings.gift_wrap_fee_cents * wrapped
            label = "Gift wrap" if wrapped == 1 else f"Gift wrap x{wrapped}"
            fees.append(Adjustment(code="GIFTWRAP", description=label, amount_cents=fee))
        return fees
