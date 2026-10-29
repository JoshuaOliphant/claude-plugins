"""Nightly feed import.

``ImportService.import_file`` drives one feed through the row pipeline,
applies accepted rows to the catalog and keeps the run record current.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from stockline.adapters.feeds import open_feed
from stockline.adapters.repositories import RunRepository, SupplierRepository
from stockline.config import Settings
from stockline.domain.categories import CategoryTree
from stockline.domain.errors import RejectThresholdExceeded, UnknownSupplierError
from stockline.domain.models import ACTIVE, ImportRun, Supplier
from stockline.services.catalog import CREATED, UNCHANGED, UPDATED, CatalogService
from stockline.services.events import EventBus, ImportFinished
from stockline.services.matching import CONFLICT, UNMATCHED, Matcher
from stockline.services.normalize import ColumnMapper, Normalizer
from stockline.services.pipeline import DUPLICATE, REJECTED, RowPipeline
from stockline.services.pricing import PriceCalculator
from stockline.services.validation import Validator
from stockline.utils.timeutil import iso, run_id_for


@dataclass
class Reject:
    line_no: int
    sku: str
    reasons: list[str]


@dataclass
class ImportReport:
    run: ImportRun
    rejects: list[Reject] = field(default_factory=list)
    match_stats: dict = field(default_factory=dict)

    def __getattr__(self, name):
        if name in ImportRun.COUNTERS or name in ("run_id", "status", "supplier_code", "source"):
            return getattr(self.run, name)
        raise AttributeError(name)


class ImportService:
    def __init__(self, settings: Settings, suppliers: SupplierRepository,
                 catalog: CatalogService, runs: RunRepository, bus: EventBus,
                 clock, categories: CategoryTree, pricing: PriceCalculator):
        self.settings = settings
        self.suppliers = suppliers
        self.catalog = catalog
        self.runs = runs
        self.bus = bus
        self.clock = clock
        self.categories = categories
        self.pricing = pricing

    # -- setup ---------------------------------------------------------------

    def resolve_supplier(self, path: Path, code: str | None) -> Supplier:
        if code:
            supplier = self.suppliers.get(code)
            if supplier is None:
                raise UnknownSupplierError(code)
            return supplier
        prefix = path.stem.split("_", 1)[0]
        supplier = self.suppliers.by_prefix(prefix)
        if supplier is None:
            raise UnknownSupplierError(path.name)
        return supplier

    def build_pipeline(self, supplier: Supplier) -> RowPipeline:
        stages = [
            Normalizer(supplier, self.categories),
            Validator(self.categories),
            self.pricing,
        ]
        return RowPipeline(ColumnMapper(supplier), stages, self.settings.dedupe_window)

    def _check_rejects(self, run: ImportRun) -> None:
        if run.rows_seen < self.settings.min_rows_for_reject_check:
            return
        if run.rejected / run.rows_seen > self.settings.max_reject_ratio:
            raise RejectThresholdExceeded(run.rejected, run.rows_seen, self.settings.max_reject_ratio)

    # -- main entry ----------------------------------------------------------

    def import_file(self, path, supplier: str | None = None, full_feed: bool = False) -> ImportReport:
        path = Path(path)
        sup = self.resolve_supplier(path, supplier)
        if not sup.active:
            raise UnknownSupplierError(f"{sup.code} (inactive)")
        started = self.clock.now()
        run_id = base_id = run_id_for(started, sup.code)
        attempt = 1
        while self.runs.get(run_id) is not None:
            attempt += 1
            run_id = f"{base_id}-{attempt}"
        run = ImportRun(
            run_id=run_id,
            supplier_code=sup.code,
            source=path.name,
            started_at=iso(started),
        )
        self.runs.save(run)
        report = ImportReport(run=run)
        matcher = Matcher(self.catalog.repo, self.settings.allow_name_match,
                          self.settings.fuzzy_threshold)
        pipeline = self.build_pipeline(sup)
        touched: set[str] = set()

        try:
            for outcome in pipeline.process(open_feed(path, sup.feed_format)):
                run.rows_seen += 1
                row = outcome.row
                if outcome.status == DUPLICATE:
                    run.duplicates += 1
                elif outcome.status == REJECTED:
                    run.rejected += 1
                    report.rejects.append(Reject(row.line_no, row.sku, list(row.errors)))
                else:
                    match = matcher.match(row)
                    if match.method in (CONFLICT, UNMATCHED):
                        run.rejected += 1
                        report.rejects.append(Reject(row.line_no, row.sku, [match.detail]))
                    else:
                        result, product = self.catalog.apply(row, match, run.run_id)
                        touched.add(product.product_id)
                        if result == CREATED:
                            run.created += 1
                        elif result == UPDATED:
                            run.updated += 1
                        elif result == UNCHANGED:
                            run.unchanged += 1
                if run.rows_seen % self.settings.progress_every == 0:
                    self._check_rejects(run)
                    self.runs.save(run)
            self._check_rejects(run)

            if full_feed:
                for product in self.catalog.repo.by_supplier(sup.code):
                    if product.status == ACTIVE and product.product_id not in touched:
                        self.catalog.discontinue(product, run.run_id)
                        run.discontinued += 1
        except Exception:
            run.status = "failed"
            run.finished_at = iso(self.clock.now())
            self.runs.save(run)
            raise

        run.status = "ok"
        run.finished_at = iso(self.clock.now())
        self.runs.save(run)
        report.match_stats = dict(matcher.stats)
        self.bus.publish(ImportFinished(run, report.rejects))
        return report
