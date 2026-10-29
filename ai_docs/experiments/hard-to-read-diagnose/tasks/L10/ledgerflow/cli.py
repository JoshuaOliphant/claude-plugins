"""Command line interface.

    python -m ledgerflow import CONFIG [--validate | --no-validate] [--source NAME ...]
    python -m ledgerflow check CONFIG
    python -m ledgerflow report LEDGER [--base USD]
    python -m ledgerflow feeds CONFIG
"""

from __future__ import annotations

import argparse
import sys

from ledgerflow import __version__
from ledgerflow.app import check_sources, list_feeds, load_ledger, run_import
from ledgerflow.config import ConfigError
from ledgerflow.feeds.transport import FeedError
from ledgerflow.report import render, summarize
from ledgerflow.utils.log import configure
from ledgerflow.utils.retry import RetryExhausted
from ledgerflow.validation import ValidationError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ledgerflow", description=__doc__.splitlines()[0])
    parser.add_argument("--version", action="version", version=f"ledgerflow {__version__}")
    parser.add_argument("-v", "--verbose", action="count", default=0)
    sub = parser.add_subparsers(dest="command", required=True)

    p_import = sub.add_parser("import", help="import configured sources into the ledger")
    p_import.add_argument("config")
    group = p_import.add_mutually_exclusive_group()
    group.add_argument("--validate", dest="validate", action="store_true", default=None,
                       help="preflight each source and apply strict record checks")
    group.add_argument("--no-validate", dest="validate", action="store_false")
    p_import.add_argument("--source", action="append", dest="only", metavar="NAME",
                          help="import only this source (repeatable)")

    p_check = sub.add_parser("check", help="sample each source and report problems")
    p_check.add_argument("config")

    p_report = sub.add_parser("report", help="summarise a written ledger")
    p_report.add_argument("ledger")
    p_report.add_argument("--base", default="USD")

    p_feeds = sub.add_parser("feeds", help="list partner feeds available to a config")
    p_feeds.add_argument("config")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure(args.verbose)
    try:
        if args.command == "import":
            result = run_import(args.config, validate=args.validate, only=args.only)
            for source in result.sources:
                print(source.line())
            print(f"total: {result.imported} transactions written to {result.output}")
            return 0
        if args.command == "check":
            for line in check_sources(args.config):
                print(line)
            return 0
        if args.command == "report":
            print(render(summarize(load_ledger(args.ledger), args.base)))
            return 0
        if args.command == "feeds":
            for meta in list_feeds(args.config):
                print(f"{meta['feed']:<10} {meta.get('title', '')}  (page size {meta.get('page_size', '?')})")
            return 0
    except (ConfigError, ValidationError, FeedError, RetryExhausted, KeyError) as exc:
        print(f"ledgerflow: error: {exc}", file=sys.stderr)
        return 2
    return 1
