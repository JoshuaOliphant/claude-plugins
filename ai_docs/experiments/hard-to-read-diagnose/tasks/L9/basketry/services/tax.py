"""Sales tax by region and tax class.

Discounts reduce the taxable base.  Order-level discounts are spread across
lines in proportion to their value before tax is computed per tax class;
fees (gift wrap) are taxed at the ``general`` rate.
"""

from __future__ import annotations

from ..config import Settings
from ..domain.money import allocate, apply_bps
from ..domain.order import Order
from ..domain.summary import Adjustment


class TaxCalculator:
    def __init__(self, settings: Settings):
        self.settings = settings

    def rates_for(self, region: str) -> dict[str, int]:
        rates = dict(self.settings.tax_rates_bps.get(region, {}))
        rates.setdefault("general", 0)
        rates.setdefault("clothing", rates["general"])
        rates.setdefault("food", 0)
        return rates

    def compute(self, order: Order, adjustments: list[Adjustment]) -> int:
        if not order.lines:
            return 0
        rates = self.rates_for(order.customer.region)
        discount = -sum(a.amount_cents for a in adjustments if a.amount_cents < 0)
        fees = sum(a.amount_cents for a in adjustments if a.amount_cents > 0)

        weights = [line.total_cents for line in order.lines]
        shares = allocate(discount, weights)

        base_by_class: dict[str, int] = {}
        for line, share in zip(order.lines, shares):
            base_by_class[line.tax_class] = base_by_class.get(line.tax_class, 0) + line.total_cents - share
        base_by_class["general"] = base_by_class.get("general", 0) + fees

        return sum(apply_bps(max(base, 0), rates[tax_class]) for tax_class, base in base_by_class.items())
