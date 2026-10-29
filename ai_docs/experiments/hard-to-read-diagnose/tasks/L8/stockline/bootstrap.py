"""Wire the application together.

``build_app`` is the single place that knows how the pieces fit; the CLI
and integration jobs call it with a store and get back a ready ``App``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from stockline.adapters.repositories import (
    CatalogRepository,
    JournalRepository,
    RunRepository,
    Sequences,
    SupplierRepository,
)
from stockline.adapters.store import MemoryStore
from stockline.config import Settings, load_settings
from stockline.domain.categories import CategoryTree
from stockline.domain.models import Supplier
from stockline.services.catalog import CatalogService
from stockline.services.events import EventBus
from stockline.services.importer import ImportService
from stockline.services.journal import ChangeJournal
from stockline.services.pricing import PriceCalculator
from stockline.utils.timeutil import SystemClock


@dataclass
class App:
    settings: Settings
    store: MemoryStore
    clock: object
    bus: EventBus
    categories: CategoryTree
    suppliers: SupplierRepository
    catalog: CatalogService
    journal: ChangeJournal
    runs: RunRepository
    importer: ImportService


def load_supplier_defaults(settings: Settings) -> list[Supplier]:
    raw = json.loads(settings.suppliers.read_text(encoding="utf-8"))
    return [Supplier.from_record(rec) for rec in raw["suppliers"]]


def build_app(store: MemoryStore | None = None, settings: Settings | None = None,
              clock=None) -> App:
    settings = settings or load_settings()
    store = store if store is not None else MemoryStore()
    clock = clock or SystemClock()
    bus = EventBus()
    categories = CategoryTree.from_file(settings.categories)
    sequences = Sequences(store)

    suppliers = SupplierRepository(store)
    suppliers.ensure(load_supplier_defaults(settings))

    catalog = CatalogService(CatalogRepository(store, sequences), bus, clock)
    journal = ChangeJournal(JournalRepository(store, sequences), clock)
    journal.attach(bus)
    runs = RunRepository(store)
    pricing = PriceCalculator(settings.pricing_rules, categories)
    importer = ImportService(settings, suppliers, catalog, runs, bus, clock, categories, pricing)

    return App(
        settings=settings,
        store=store,
        clock=clock,
        bus=bus,
        categories=categories,
        suppliers=suppliers,
        catalog=catalog,
        journal=journal,
        runs=runs,
        importer=importer,
    )
