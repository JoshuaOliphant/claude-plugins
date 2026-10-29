"""Wire settings, storage and services together."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tillbook.adapters.fx import FxTable
from tillbook.config import Settings, load_settings
from tillbook.domain.offices import OfficeRegistry
from tillbook.services.ledger import LedgerService
from tillbook.services.reports import ReportService
from tillbook.services.validation import Validator
from tillbook.storage.archive import SnapshotArchive
from tillbook.storage.repository import TransactionRepository


@dataclass
class Application:
    settings: Settings
    offices: OfficeRegistry
    repository: TransactionRepository
    ledger: LedgerService
    reports: ReportService
    fx: FxTable

    def validator(self) -> Validator:
        return Validator(self.repository)

    def archive(self) -> SnapshotArchive | None:
        if self.settings.archive_dir is None:
            return None
        return SnapshotArchive(self.settings.archive_dir)


def build(config_path: Path | None = None, data_dir: Path | None = None) -> Application:
    settings = load_settings(config_path)
    if data_dir is not None:
        settings = Settings(**{**settings.__dict__, "data_dir": data_dir.resolve()})
    offices = OfficeRegistry.load(settings.path(settings.offices_file))
    repository = TransactionRepository.from_settings(settings, offices)
    fx = FxTable.load(settings.path(settings.fx_file), base="USD")
    ledger = LedgerService(repository, cache_capacity=settings.cache_capacity)
    reports = ReportService(ledger, fx, settings.report_currency, settings.week_starts_on)
    return Application(settings, offices, repository, ledger, reports, fx)
