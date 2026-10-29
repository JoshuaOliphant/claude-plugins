"""Ingest one movement file: read, validate, post."""

from __future__ import annotations

from pathlib import Path

from stockflow.adapters.csv_reader import MovementCsvReader
from stockflow.config.settings import Settings
from stockflow.container import ServiceContainer
from stockflow.domain.errors import InputFormatError, ValidationError
from stockflow.domain.models import IngestResult
from stockflow.services.ledger import Ledger
from stockflow.services.validation import RowValidator


class IngestService:
    def __init__(self, reader: MovementCsvReader, validator: RowValidator,
                 ledger: Ledger, settings: Settings) -> None:
        self.reader = reader
        self.validator = validator
        self.ledger = ledger
        self.settings = settings

    @classmethod
    def from_container(cls, container: ServiceContainer) -> "IngestService":
        return cls(
            reader=container.get("reader"),
            validator=container.get("validator"),
            ledger=container.get("ledger"),
            settings=container.get("settings"),
        )

    def _note(self, result: IngestResult, message: str) -> None:
        if len(result.errors) < self.settings.max_errors_per_file:
            result.errors.append(message)

    def ingest_file(self, path: Path, dry_run: bool = False) -> IngestResult:
        result = IngestResult(source=path.name)
        try:
            rows = list(self.reader.read(path))
        except InputFormatError as exc:
            self._note(result, str(exc))
            result.rejected += 1
            return result

        for row in rows:
            result.rows_read += 1
            try:
                movement = self.validator.validate(row)
            except ValidationError as exc:
                result.rejected += 1
                self._note(result, str(exc))
                continue
            if dry_run:
                continue
            outcome = self.ledger.post(movement)
            if outcome.posted:
                result.posted += 1
            else:
                result.duplicates += 1
        self.ledger.metrics.incr("files.ingested")
        return result

    def ingest_many(self, paths: list[Path], dry_run: bool = False) -> list[IngestResult]:
        return [self.ingest_file(p, dry_run=dry_run) for p in paths]
