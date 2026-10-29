"""The order summary use case, wiring adapters and services together."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..adapters.catalog import Catalog
from ..adapters.codec import OrderDecoder
from ..adapters.customers import CustomerStore
from ..adapters.journal import Journal
from ..adapters.templates import OrderTemplates
from ..config import Settings, data_dir, load_settings
from ..domain.order import Order
from ..domain.summary import OrderSummary
from .packing import PackingPlanner
from .pricing import Pricer
from .promotions import PromotionBook, PromotionEngine
from .shipping import ShippingQuoter
from .summary import SummaryBuilder
from .tax import TaxCalculator


@dataclass
class ServiceStats:
    requests: int = 0
    summarized: int = 0
    rejected: int = 0


class OrderService:
    def __init__(
        self,
        settings: Settings,
        catalog: Catalog,
        customers: CustomerStore,
        templates: OrderTemplates,
        promotions: PromotionBook,
        journal: Journal | None = None,
    ):
        self.settings = settings
        self.catalog = catalog
        self.decoder = OrderDecoder(templates, catalog, customers)
        self.pricer = Pricer(settings)
        self.promotions = PromotionEngine(settings, promotions)
        self.tax = TaxCalculator(settings)
        self.shipping = ShippingQuoter(settings)
        self.packing = PackingPlanner(settings, catalog)
        self.journal = journal if journal is not None else Journal()
        self.stats = ServiceStats()

    @classmethod
    def from_data_dir(cls, directory: Path | None = None) -> "OrderService":
        root = Path(directory) if directory is not None else data_dir()
        return cls(
            settings=load_settings(root / "settings.json"),
            catalog=Catalog(root / "catalog.json"),
            customers=CustomerStore(root / "customers.json"),
            templates=OrderTemplates(root / "order_defaults.json"),
            promotions=PromotionBook.load(root / "promotions.json"),
        )

    def decode(self, payload: Any) -> Order:
        return self.decoder.decode(payload)

    def summarize(self, payload: Any) -> OrderSummary:
        self.stats.requests += 1
        try:
            order = self.decode(payload)
        except ValueError:
            self.stats.rejected += 1
            raise
        self.journal.record(
            "decoded",
            order.order_id,
            customer=order.customer.customer_id,
            channel=order.channel,
            lines=len(order.lines),
        )
        summary = self.summarize_order(order)
        self.stats.summarized += 1
        self.journal.record("summarized", order.order_id, total_cents=summary.total_cents)
        return summary

    def summarize_order(self, order: Order) -> OrderSummary:
        builder = SummaryBuilder()
        priced = self.pricer.price(order)
        discounts = self.promotions.evaluate(order, priced)
        fees = self.pricer.fees(order)
        for message in self.promotions.last_rejections:
            builder.add_note(message)

        discounted = priced.subtotal_cents + sum(a.amount_cents for a in discounts)
        plan = self.packing.plan(order, discounted)
        shipping = self.shipping.quote(order, discounted, plan.shipped_grams)
        tax_cents = self.tax.compute(order, discounts + fees)

        builder.add_adjustments(discounts)
        builder.add_adjustments(fees)
        return builder.build(order, priced, shipping, plan, tax_cents)
