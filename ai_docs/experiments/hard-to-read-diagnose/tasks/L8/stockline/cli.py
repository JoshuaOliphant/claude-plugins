"""Command-line interface: ``python -m stockline <command>``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stockline import __version__
from stockline.adapters.store import JsonFileStore
from stockline.bootstrap import build_app
from stockline.config import load_settings
from stockline.domain.errors import StocklineError
from stockline.services import reporting


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stockline", description="Supplier feed import for the catalog")
    p.add_argument("--version", action="version", version=f"stockline {__version__}")
    p.add_argument("--db", help="catalog store file (default from config / STOCKLINE_DB)")
    p.add_argument("--config", help="extra .ini file layered over the defaults")
    sub = p.add_subparsers(dest="command", required=True)

    imp = sub.add_parser("import", help="import one supplier feed")
    imp.add_argument("feed", type=Path)
    imp.add_argument("--supplier", help="supplier code (default: from file name prefix)")
    imp.add_argument("--full-feed", action="store_true",
                     help="feed lists the supplier's whole range; discontinue anything missing")
    imp.add_argument("--quiet", action="store_true", help="print only the one-line result")

    show = sub.add_parser("show", help="show one product")
    show.add_argument("sku")

    hist = sub.add_parser("history", help="change history for a product")
    hist.add_argument("sku")

    runs = sub.add_parser("runs", help="list import runs")
    runs.add_argument("--supplier")
    runs.add_argument("--limit", type=int, default=20)

    exp = sub.add_parser("export", help="write the catalog as CSV")
    exp.add_argument("output", nargs="?", default="-")
    exp.add_argument("--supplier")

    sub.add_parser("suppliers", help="list configured suppliers")
    sub.add_parser("summary", help="per-supplier catalog summary")
    return p


def _cmd_import(app, args) -> int:
    report = app.importer.import_file(args.feed, supplier=args.supplier, full_feed=args.full_feed)
    if args.quiet:
        print(f"{report.run_id}: {report.created} created, {report.updated} updated, "
              f"{report.unchanged} unchanged, {report.rejected} rejected")
    else:
        print(reporting.render_report(report, app.settings.currency))
    return 0


def _cmd_show(app, args) -> int:
    product = app.catalog.lookup(args.sku)
    if product is None:
        print(f"no product with SKU {args.sku}", file=sys.stderr)
        return 1
    print(reporting.render_product(product, app.categories, app.settings.currency))
    return 0


def _cmd_history(app, args) -> int:
    print(reporting.render_history(app.journal.history(args.sku)))
    return 0


def _cmd_runs(app, args) -> int:
    runs = [r for r in app.runs.all() if not args.supplier or r.supplier_code == args.supplier.upper()]
    print(reporting.render_runs(runs[-args.limit:]))
    return 0


def _cmd_export(app, args) -> int:
    text = reporting.export_csv(app.catalog.products(args.supplier.upper() if args.supplier else None))
    if args.output == "-":
        sys.stdout.write(text)
    else:
        Path(args.output).write_text(text, encoding="utf-8")
    return 0


def _cmd_suppliers(app, args) -> int:
    for s in app.suppliers.all():
        flag = "" if s.active else " (inactive)"
        print(f"{s.code:<6} {s.name:<28} {s.feed_format:<6} {s.filename_prefix}_*{flag}")
    return 0


def _cmd_summary(app, args) -> int:
    summary = reporting.supplier_summary(app.catalog.repo.all())
    print(reporting.render_summary(summary, app.settings.currency))
    return 0


COMMANDS = {
    "import": _cmd_import,
    "show": _cmd_show,
    "history": _cmd_history,
    "runs": _cmd_runs,
    "export": _cmd_export,
    "suppliers": _cmd_suppliers,
    "summary": _cmd_summary,
}


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        settings = load_settings(args.config)
        db = args.db or settings.db_path
        with JsonFileStore(db) as store:
            app = build_app(store=store, settings=settings)
            return COMMANDS[args.command](app, args)
    except StocklineError as exc:
        print(f"stockline: {exc}", file=sys.stderr)
        return 2
