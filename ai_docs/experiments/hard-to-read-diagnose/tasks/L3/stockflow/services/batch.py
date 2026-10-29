"""Parallel ingestion of many movement files."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from stockflow.container import ServiceContainer
from stockflow.domain.models import IngestResult
from stockflow.services.ingest import IngestService
from stockflow.utils.ids import run_id

ProgressCallback = Callable[[int, int, IngestResult], None]


@dataclass
class BatchSummary:
    run_id: str
    results: list[IngestResult] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    @property
    def totals(self) -> IngestResult:
        total = IngestResult(source="*")
        for r in self.results:
            total.merge(r)
        return total


class BatchRunner:
    """Ingest files concurrently, one file per task.

    Each task builds its own :class:`IngestService` from the shared
    container. Services themselves are stateless apart from the repository
    and metrics, both of which synchronise internally.
    """

    def __init__(self, container: ServiceContainer, workers: int,
                 progress: Optional[ProgressCallback] = None) -> None:
        if workers < 1:
            raise ValueError("workers must be at least 1")
        self.container = container
        self.workers = workers
        self.progress = progress

    def _process(self, path: Path) -> IngestResult:
        service = IngestService.from_container(self.container)
        return service.ingest_file(path)

    def run(self, paths: list[Path]) -> BatchSummary:
        summary = BatchSummary(run_id=run_id("BATCH"))
        if not paths:
            return summary
        done = 0
        with ThreadPoolExecutor(max_workers=self.workers, thread_name_prefix="ingest") as pool:
            futures = {pool.submit(self._process, p): p for p in paths}
            for future in as_completed(futures):
                path = futures[future]
                try:
                    result = future.result()
                except Exception as exc:  # keep going; report at the end
                    summary.failures.append(f"{path.name}: {exc}")
                    continue
                summary.results.append(result)
                done += 1
                if self.progress is not None:
                    self.progress(done, len(paths), result)
        summary.results.sort(key=lambda r: r.source)
        return summary
