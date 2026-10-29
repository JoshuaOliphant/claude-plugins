"""Command line interface: ``python -m tillbook <command> ...``."""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from tillbook import __version__
from tillbook.app import Application, build
from tillbook.domain.offices import UnknownOffice
from tillbook.services import closing
from tillbook.utils.formatting import render_table, to_json
from tillbook.utils.logging_setup import configure
from tillbook.utils.timeconv import TimestampError, format_iso, parse_date


def _day(text: str) -> date:
    try:
        return parse_date(text)
    except TimestampError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _default_day() -> date:
    return date.today() - timedelta(days=1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tillbook", description=__doc__)
    parser.add_argument("--version", action="version", version=f"tillbook {__version__}")
    parser.add_argument("--config", type=Path, help="extra settings.ini to layer on top")
    parser.add_argument("--data-dir", type=Path, help="override the data directory")
    parser.add_argument("--log-level", choices=["debug", "info", "warning", "error"])
    sub = parser.add_subparsers(dest="command", required=True)

    offices = sub.add_parser("offices", help="list registered offices")
    offices.add_argument("--json", action="store_true")

    daily = sub.add_parser("daily-totals", help="totals per office-local day")
    daily.add_argument("--office", required=True)
    daily.add_argument("--date", type=_day, help="first day (default: yesterday)")
    daily.add_argument("--to", type=_day, help="last day, inclusive (default: --date)")
    daily.add_argument("--json", action="store_true")
    daily.add_argument("--archive", action="store_true", help="also write a snapshot")

    weekly = sub.add_parser("weekly", help="one week of daily totals")
    weekly.add_argument("--office", required=True)
    weekly.add_argument("--date", type=_day, help="any day in the week (default: yesterday)")
    weekly.add_argument("--json", action="store_true")

    items = sub.add_parser("top-items", help="best-selling items over a date range")
    items.add_argument("--office", required=True)
    items.add_argument("--from", dest="first", type=_day, required=True)
    items.add_argument("--to", dest="last", type=_day, required=True)
    items.add_argument("--limit", type=int, default=10)
    items.add_argument("--json", action="store_true")

    consolidated = sub.add_parser("consolidated", help="net takings across offices")
    consolidated.add_argument("--date", type=_day)
    consolidated.add_argument("--json", action="store_true")

    validate = sub.add_parser("validate", help="run data quality checks")
    validate.add_argument("--json", action="store_true")

    close = sub.add_parser("close-status", help="which office days are closed")
    close.add_argument("--date", type=_day)
    close.add_argument("--json", action="store_true")
    return parser


def _emit(rendered, as_json: bool) -> None:
    print(rendered.as_json() if as_json else rendered.text)


def cmd_offices(app: Application, args) -> int:
    offices = list(app.offices)
    if args.json:
        print(to_json([{"code": o.code, "name": o.name, "timezone": o.timezone,
                        "currency": o.currency, "tills": list(o.tills)} for o in offices]))
        return 0
    print(render_table(
        ["code", "name", "timezone", "ccy", "hours", "tills"],
        [[o.code, o.name, o.timezone, o.currency,
          f"{o.opens:%H:%M}-{o.closes:%H:%M}", len(o.tills)] for o in offices],
    ))
    return 0


def cmd_daily(app: Application, args) -> int:
    first = args.date or _default_day()
    last = args.to or first
    if last < first:
        print("error: --to is before --date", file=sys.stderr)
        return 2
    rendered = app.reports.daily_totals(args.office, first, last)
    _emit(rendered, args.json)
    if args.archive:
        archive = app.archive()
        if archive is None:
            print("warning: no archive_dir configured", file=sys.stderr)
        else:
            archive.write("daily", f"{args.office}-{first}", rendered.payload)
            archive.prune()
    return 0


def cmd_weekly(app: Application, args) -> int:
    _emit(app.reports.weekly(args.office, args.date or _default_day()), args.json)
    return 0


def cmd_top_items(app: Application, args) -> int:
    if args.last < args.first:
        print("error: --to is before --from", file=sys.stderr)
        return 2
    _emit(app.reports.top_items(args.office, args.first, args.last, args.limit), args.json)
    return 0


def cmd_consolidated(app: Application, args) -> int:
    _emit(app.reports.consolidated(args.date or _default_day()), args.json)
    return 0


def cmd_validate(app: Application, args) -> int:
    result = app.validator().run()
    if args.json:
        print(to_json(result.to_json()))
    else:
        for finding in result.findings:
            txn = f" [{finding.txn_id}]" if finding.txn_id else ""
            print(f"{finding.severity:<7} {finding.code:<18} {finding.message}{txn}")
        print(f"\n{len(result.errors)} errors, {len(result.warnings)} warnings, "
              f"{app.repository.count()} transactions")
    return 1 if result.errors else 0


def cmd_close_status(app: Application, args) -> int:
    day = args.date or _default_day()
    rows = closing.board(app.offices, day)
    if args.json:
        print(to_json([row.to_json() for row in rows]))
    else:
        print(render_table(["office", "date", "closes at (UTC)", "closed"],
                           [[r.office, r.day.isoformat(), format_iso(r.closes_at),
                             "yes" if r.closed else "no"] for r in rows]))
    return 0


COMMANDS = {
    "offices": cmd_offices,
    "daily-totals": cmd_daily,
    "weekly": cmd_weekly,
    "top-items": cmd_top_items,
    "consolidated": cmd_consolidated,
    "validate": cmd_validate,
    "close-status": cmd_close_status,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure(args.log_level)
    try:
        app = build(args.config, args.data_dir)
        return COMMANDS[args.command](app, args)
    except UnknownOffice as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
