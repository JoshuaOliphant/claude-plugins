"""Wire the application's services into a container."""

from __future__ import annotations

from pathlib import Path

from stockflow.adapters.csv_reader import MovementCsvReader
from stockflow.adapters.repository import InMemoryStockRepository
from stockflow.adapters.snapshot import load_opening_balances
from stockflow.config.settings import Settings, load_settings
from stockflow.container import ServiceContainer
from stockflow.domain.catalog import Catalog
from stockflow.domain.models import StockLevel
from stockflow.domain.units import UnitTable
from stockflow.services.ledger import Ledger
from stockflow.services.metrics import Metrics
from stockflow.services.reporting import ReportService
from stockflow.services.validation import RowValidator


def _catalog(c: ServiceContainer) -> Catalog:
    return Catalog.from_file(c.get("settings").catalog_path)


def _units(c: ServiceContainer) -> UnitTable:
    return UnitTable.from_file(c.get("settings").units_path)


def _opening_balances(c: ServiceContainer) -> list[StockLevel]:
    settings: Settings = c.get("settings")
    return load_opening_balances(settings.opening_balances_path, c.get("catalog"))


def _repository(c: ServiceContainer) -> InMemoryStockRepository:
    return InMemoryStockRepository(c.get("opening_balances"))


def _ledger(c: ServiceContainer) -> Ledger:
    return Ledger(c.get("repository"), c.get("metrics"))


def _validator(c: ServiceContainer) -> RowValidator:
    return RowValidator(c.get("catalog"), c.get("units"), c.get("settings"))


def _reader(c: ServiceContainer) -> MovementCsvReader:
    return MovementCsvReader()


def _reporting(c: ServiceContainer) -> ReportService:
    return ReportService(c.get("repository"), c.get("catalog"), c.get("settings"))


def build_container(config_path: str | Path | None = None) -> ServiceContainer:
    settings = load_settings(config_path)
    container = ServiceContainer()
    container.register_instance("settings", settings)
    container.register_instance("metrics", Metrics())
    container.register("catalog", _catalog)
    container.register("units", _units)
    container.register("opening_balances", _opening_balances)
    container.register("repository", _repository)
    container.register("ledger", _ledger)
    container.register("validator", _validator)
    container.register("reader", _reader)
    container.register("reporting", _reporting)
    return container
