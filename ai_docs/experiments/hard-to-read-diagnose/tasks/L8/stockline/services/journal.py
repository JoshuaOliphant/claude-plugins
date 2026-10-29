"""Change journal: an audit trail of every catalog change.

Merchandising uses ``stockline history <sku>`` to answer "why did this
price move?", so every created/updated/discontinued product is recorded
with before/after values and the import run that caused it.
"""

from __future__ import annotations

from stockline.adapters.repositories import JournalRepository
from stockline.domain.models import Change
from stockline.services.events import (
    EventBus,
    ProductCreated,
    ProductDiscontinued,
    ProductUpdated,
)
from stockline.utils.timeutil import iso


def _plain(value) -> str:
    return "" if value is None else str(value)


class ChangeJournal:
    def __init__(self, repo: JournalRepository, clock):
        self.repo = repo
        self.clock = clock

    def attach(self, bus: EventBus) -> None:
        bus.subscribe(ProductCreated, self.on_created)
        bus.subscribe(ProductUpdated, self.on_updated)
        bus.subscribe(ProductDiscontinued, self.on_discontinued)

    def _record(self, run_id: str, product, kind: str, fields: dict) -> None:
        self.repo.append(Change(
            seq=0,
            at=iso(self.clock.now()),
            run_id=run_id,
            product_id=product.product_id,
            sku=product.sku,
            kind=kind,
            fields=fields,
        ))

    def on_created(self, event: ProductCreated) -> None:
        p = event.product
        self._record(event.run_id, p, "created", {
            "name": [None, p.name],
            "cost": [None, _plain(p.cost)],
            "price": [None, _plain(p.price)],
        })

    def on_updated(self, event: ProductUpdated) -> None:
        fields = {
            name: [_plain(before), _plain(after)]
            for name, (before, after) in sorted(event.changes.items())
        }
        self._record(event.run_id, event.product, "updated", fields)

    def on_discontinued(self, event: ProductDiscontinued) -> None:
        self._record(event.run_id, event.product, "discontinued",
                     {"status": ["active", "discontinued"]})

    # -- queries -------------------------------------------------------------

    def history(self, sku: str) -> list[Change]:
        return self.repo.for_sku(sku)

    def for_run(self, run_id: str) -> list[Change]:
        return self.repo.for_run(run_id)
