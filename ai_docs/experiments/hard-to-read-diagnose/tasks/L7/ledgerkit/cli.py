"""Command line interface: ``python -m ledgerkit <command> ...``."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import logging
import sys

from ledgerkit import __version__
from ledgerkit.config import load_config
from ledgerkit.formatting.numbers import locale_from_environment
from ledgerkit.importers import ImportError_
from ledgerkit.money import MoneyError
from ledgerkit.plugins.registry import RegistryError
from ledgerkit.services.export_service import describe_formats, export_ledger
from ledgerkit.services.loading import load_ledger
from ledgerkit.services.summary_service import format_summary
from ledgerkit.services.validation import validate
from ledgerkit.utils.dates import DateParseError, parse_date
from ledgerkit.utils.text import render_table

COMMANDS: dict[str, "Command"] = {}


class Command:
    def __init__(self, name, func, help_text, configure):
        self.name = name
        self.func = func
        self.help = help_text
        self.configure = configure


def command(name: str, help_text: str):
    def decorator(func):
        def configure(parser):
            return parser

        COMMANDS[name] = Command(name, func, help_text, getattr(func, "_configure", configure))
        return func

    return decorator


def arguments(configure):
    def decorator(func):
        func._configure = configure
        return func

    return decorator


def _input_args(p):
    p.add_argument("ledger", help="ledger file (.ledger, .csv, .json, .jsonl)")
    p.add_argument("--input-format", "-i", help="override input format detection")
    p.add_argument("--period", help="restrict to a year, month (2026-03) or quarter (2026Q1)")
    p.add_argument("--account", help="restrict to one account")


def _export_args(p):
    _input_args(p)
    p.add_argument("--output", "-o", help="output file; the format follows its extension")
    p.add_argument("--format", "-f", dest="fmt", help="output format (see 'formats')")
    p.add_argument("--running-balance", action="store_true", default=None)


@command("export", "convert a ledger to another format")
@arguments(_export_args)
def cmd_export(args, config, out):
    result = export_ledger(
        args.ledger,
        args.output,
        fmt=args.fmt,
        input_format=args.input_format,
        period=args.period,
        account=args.account,
        running_balance=args.running_balance,
        config=config,
        stdout=out,
    )
    if result.destination != "<stdout>":
        print(
            f"wrote {result.transactions} transactions to {result.destination} ({result.format_name})",
            file=sys.stderr,
        )
    return 0


def _summary_args(p):
    _input_args(p)
    p.add_argument("--by", choices=("category", "month"), default="category")


@command("summary", "print totals for a ledger")
@arguments(_summary_args)
def cmd_summary(args, config, out):
    loaded = load_ledger(
        args.ledger, input_format=args.input_format, config=config,
        period=args.period, account=args.account,
    )
    locale = locale_from_environment(config.get("display", "locale"))
    out.write(format_summary(loaded.ledger, locale, by=args.by))
    return 0


def _validate_args(p):
    _input_args(p)
    p.add_argument("--today", help="reference date for future-date checks (default: today)")
    p.add_argument("--json", action="store_true", help="machine-readable output")


@command("validate", "check a ledger for common mistakes")
@arguments(_validate_args)
def cmd_validate(args, config, out):
    loaded = load_ledger(args.ledger, input_format=args.input_format, config=config, strict=False)
    today = parse_date(args.today) if args.today else _dt.date.today()
    result = validate(loaded.ledger, config, today)
    for err in loaded.report.errors:
        out.write(f"[error] {err}\n")
    if args.json:
        payload = [{"level": i.level, "id": i.txn_id, "message": i.message} for i in result.issues]
        out.write(json.dumps(payload, indent=2) + "\n")
    else:
        for issue in result.issues:
            out.write(f"{issue}\n")
        out.write(f"{len(result.errors)} error(s), {len(result.warnings)} warning(s)\n")
    return 0 if result.ok and not loaded.report.errors else 1


def _formats_args(p):
    p.add_argument("--json", action="store_true")


@command("formats", "list the available output formats")
@arguments(_formats_args)
def cmd_formats(args, config, out):
    formats = describe_formats()
    if args.json:
        out.write(json.dumps(formats, indent=2) + "\n")
        return 0
    rows = [
        [f["name"], ", ".join(f["aliases"]), " ".join(f["extensions"]), f["description"]]
        for f in formats
    ]
    out.write(render_table(["Format", "Aliases", "Extensions", "Description"], rows) + "\n")
    return 0


@command("version", "print the ledgerkit version")
def cmd_version(args, config, out):
    out.write(f"ledgerkit {__version__}\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ledgerkit", description=__doc__)
    parser.add_argument("--config-dir", help="directory of *.ini files (default: conf.d)")
    parser.add_argument("--verbose", "-v", action="count", default=0)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in sorted(COMMANDS):
        cmd = COMMANDS[name]
        cmd.configure(sub.add_parser(name, help=cmd.help))
    return parser


def main(argv=None, out=None) -> int:
    out = out or sys.stdout
    parser = build_parser()
    args = parser.parse_args(argv)
    level = logging.WARNING - 10 * min(args.verbose, 2)
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")
    config = load_config(args.config_dir)
    try:
        return COMMANDS[args.command].func(args, config, out)
    except (ImportError_, MoneyError, DateParseError, RegistryError, OSError) as exc:
        print(f"ledgerkit: error: {exc}", file=sys.stderr)
        return 2
