"""Argument handling shared by the command modules."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from .. import config
from ..adapters import json_source
from ..services.invoicing import InvoiceService
from ..utils import dates, logsetup


class CommandError(Exception):
    """A user-facing error: printed without a traceback, exit status 2."""


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", help="settings file (default: config/ledgerly.toml)")
    parser.add_argument("--customers", type=Path, help="customer master data (JSON)")
    parser.add_argument("--fx-rates", type=Path, help="FX rate table (JSON)")
    parser.add_argument("-v", "--verbose", action="count", default=0)


def add_source_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("source", type=Path, help="invoice line export (CSV)")


def as_of_arg(text: str) -> date:
    try:
        return dates.parse_date(text)
    except dates.DateFormatError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def build_service(args) -> InvoiceService:
    logsetup.configure(args.verbose)
    try:
        settings = config.load(args.config)
    except config.ConfigError as exc:
        raise CommandError(str(exc)) from None
    return InvoiceService.from_settings(settings, args.customers, args.fx_rates)


def load_source(service: InvoiceService, path: Path):
    if not path.exists():
        raise CommandError(f"no such file: {path}")
    try:
        return service.load(path)
    except ValueError as exc:
        raise CommandError(str(exc)) from None


def load_payments(path: Path | None):
    if path is None:
        return None
    if not path.exists():
        raise CommandError(f"no such file: {path}")
    return json_source.load_payments(path)


def run(handler, args) -> int:
    try:
        return handler(args) or 0
    except CommandError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
