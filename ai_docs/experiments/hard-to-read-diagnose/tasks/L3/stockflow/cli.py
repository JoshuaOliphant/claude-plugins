"""Command-line interface.

    python -m stockflow import FILE [FILE ...]
    python -m stockflow batch DIR_OR_FILE [...] --workers 8
    python -m stockflow validate FILE [FILE ...]
    python -m stockflow catalog
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from stockflow import __version__
from stockflow.adapters.report_writer import FORMATS, render
from stockflow.adapters.snapshot import write_snapshot
from stockflow.bootstrap import build_container
from stockflow.container import ServiceContainer
from stockflow.domain.errors import StockflowError
from stockflow.domain.models import IngestResult
from stockflow.services.batch import BatchRunner
from stockflow.services.ingest import IngestService
from stockflow.utils.paths import discover_movement_files
from stockflow.utils.textfmt import format_table


def _add_output_options(p: argparse.ArgumentParser) -> None:
    p.add_argument("--format", choices=FORMATS, default="text")
    p.add_argument("--output", "-o", type=Path, help="write the report here instead of stdout")
    p.add_argument("--warehouse", help="only report this warehouse")
    p.add_argument("--snapshot", type=Path, help="also write closing balances as JSON")
    p.add_argument("--per-file", action="store_true", help="include per-file ingest counts")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stockflow", description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, help="path to stockflow.ini")
    parser.add_argument("--version", action="version", version=f"stockflow {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_import = sub.add_parser("import", help="ingest files one after another")
    p_import.add_argument("files", nargs="+")
    _add_output_options(p_import)

    p_batch = sub.add_parser("batch", help="ingest files in parallel")
    p_batch.add_argument("inputs", nargs="+", help="files or directories")
    p_batch.add_argument("--workers", "-w", type=int, default=None)
    p_batch.add_argument("--quiet", "-q", action="store_true")
    _add_output_options(p_batch)

    p_validate = sub.add_parser("validate", help="check files without posting")
    p_validate.add_argument("files", nargs="+")

    sub.add_parser("catalog", help="list known SKUs")
    return parser


def _emit(text: str, output: Optional[Path]) -> None:
    if output is None:
        sys.stdout.write(text)
    else:
        output.write_text(text, encoding="utf-8")


def _finish(container: ServiceContainer, args: argparse.Namespace,
            results: list[IngestResult]) -> int:
    report = container.get("reporting").build(args.warehouse)
    totals = IngestResult(source="*")
    for r in results:
        totals.merge(r)
    _emit(render(args.format, report, totals, results if args.per_file else None), args.output)
    if args.snapshot is not None:
        write_snapshot(args.snapshot, container.get("repository").levels(), report.as_of)
    for r in results:
        for message in r.errors:
            print(f"warning: {message}", file=sys.stderr)
    return 0


def cmd_import(container: ServiceContainer, args: argparse.Namespace) -> int:
    paths = discover_movement_files(args.files)
    service = IngestService.from_container(container)
    results = service.ingest_many(paths)
    return _finish(container, args, results)


def cmd_batch(container: ServiceContainer, args: argparse.Namespace) -> int:
    settings = container.get("settings")
    workers = args.workers or settings.default_workers
    paths = discover_movement_files(args.inputs, settings.file_pattern)
    # Fail fast on broken reference data before starting any workers.
    container.get("validator")
    container.get("opening_balances")

    def progress(done: int, total: int, result: IngestResult) -> None:
        if not args.quiet:
            print(f"[{done}/{total}] {result.source}: {result.posted} posted",
                  file=sys.stderr)

    summary = BatchRunner(container, workers, progress).run(paths)
    for failure in summary.failures:
        print(f"error: {failure}", file=sys.stderr)
    status = _finish(container, args, summary.results)
    return 1 if summary.failures else status


def cmd_validate(container: ServiceContainer, args: argparse.Namespace) -> int:
    paths = discover_movement_files(args.files)
    service = IngestService.from_container(container)
    bad = 0
    for path in paths:
        result = service.ingest_file(path, dry_run=True)
        print(f"{result.source}: {result.rows_read} rows, {result.rejected} rejected")
        for message in result.errors:
            print(f"  {message}")
        bad += result.rejected
    return 1 if bad else 0


def cmd_catalog(container: ServiceContainer, args: argparse.Namespace) -> int:
    catalog = container.get("catalog")
    rows = [(s.code, s.description, s.category, s.base_uom, s.case_size or "",
             s.reorder_point, "" if s.active else "inactive") for s in catalog]
    print(format_table(["SKU", "Description", "Category", "UoM", "Case", "Reorder", ""], rows,
                       align=["l", "l", "l", "l", "r", "r", "l"]))
    return 0


COMMANDS = {
    "import": cmd_import,
    "batch": cmd_batch,
    "validate": cmd_validate,
    "catalog": cmd_catalog,
}


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        container = build_container(args.config)
        return COMMANDS[args.command](container, args)
    except (StockflowError, FileNotFoundError) as exc:
        print(f"stockflow: {exc}", file=sys.stderr)
        return 2
