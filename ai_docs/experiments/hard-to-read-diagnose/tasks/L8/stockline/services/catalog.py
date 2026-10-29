"""Catalog service: applies accepted feed rows to products."""

from __future__ import annotations

from dataclasses import replace

from stockline.adapters.repositories import CatalogRepository
from stockline.domain.models import ACTIVE, DISCONTINUED, FeedRow, Product
from stockline.services.events import (
    EventBus,
    ProductCreated,
    ProductDiscontinued,
    ProductUpdated,
)
from stockline.services.matching import BY_PART, MatchResult
from stockline.utils.timeutil import iso

CREATED = "created"
UPDATED = "updated"
UNCHANGED = "unchanged"


class CatalogService:
    def __init__(self, repo: CatalogRepository, bus: EventBus, clock):
        self.repo = repo
        self.bus = bus
        self.clock = clock

    # -- queries -------------------------------------------------------------

    def lookup(self, sku: str) -> Product | None:
        return self.repo.find_by_sku(sku)

    def products(self, supplier_code: str | None = None) -> list[Product]:
        items = self.repo.by_supplier(supplier_code) if supplier_code else list(self.repo.all())
        return sorted(items, key=lambda p: p.sku)

    # -- commands ------------------------------------------------------------

    def _now(self) -> str:
        return iso(self.clock.now())

    def apply(self, row: FeedRow, match: MatchResult, run_id: str) -> tuple[str, Product]:
        now = self._now()
        if match.product is None:
            product = Product(
                product_id=self.repo.new_id(),
                sku=row.sku,
                name=row.name,
                supplier_code=row.supplier_code,
                supplier_part=row.supplier_part,
                category=row.category,
                uom=row.uom,
                pack_size=row.pack_size,
                cost=row.cost,
                price=row.price,
                created_at=now,
                updated_at=now,
            )
            self.repo.save(product)
            self.bus.publish(ProductCreated(product, run_id))
            return CREATED, product

        current = match.product
        proposed = replace(
            current,
            name=row.name or current.name,
            supplier_part=row.supplier_part or current.supplier_part,
            category=row.category or current.category,
            uom=row.uom,
            pack_size=row.pack_size,
            cost=row.cost,
            price=row.price,
            status=ACTIVE,
        )
        changes = current.diff(proposed)
        if match.method == BY_PART and row.sku and row.sku != current.sku:
            proposed.sku = row.sku
            changes["sku"] = (current.sku, row.sku)
        if not changes:
            return UNCHANGED, current
        proposed.updated_at = now
        self.repo.save(proposed)
        self.bus.publish(ProductUpdated(proposed, changes, run_id))
        return UPDATED, proposed

    def discontinue(self, product: Product, run_id: str) -> Product:
        if product.status == DISCONTINUED:
            return product
        updated = replace(product, status=DISCONTINUED, updated_at=self._now())
        self.repo.save(updated)
        self.bus.publish(ProductDiscontinued(updated, run_id))
        return updated
