"""Turning a ledger into an output file."""

from __future__ import annotations

import io
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from ledgerkit.config import Config, load_config
from ledgerkit.exporters import ExportOptions, Exporter, exporter_registry, load_exporters
from ledgerkit.models import Ledger
from ledgerkit.services.loading import load_ledger


@dataclass
class ExportResult:
    format_name: str
    destination: str
    transactions: int
    characters: int


def options_from_config(config: Config, **overrides) -> ExportOptions:
    columns = tuple(config.get_list("export", "columns")) or ExportOptions().columns
    opts = ExportOptions(
        columns=columns,
        date_format=config.get("export", "date_format", "") or "",
        locale=config.get("display", "locale", "C") or "C",
        title=config.get("display", "title", "Ledger report") or "Ledger report",
    )
    for key, value in overrides.items():
        if value is not None:
            setattr(opts, key, value)
    return opts


def resolve_exporter(
    fmt: str | None, output: str | os.PathLike | None, config: Config
) -> type[Exporter]:
    load_exporters()
    if fmt:
        return exporter_registry.get(fmt)
    if output and str(output) != "-":
        suffix = Path(output).suffix
        if suffix:
            return exporter_registry.for_extension(suffix)
    return exporter_registry.get(config.get("export", "default_format", "csv") or "csv")


def render_ledger(ledger: Ledger, exporter_cls: type[Exporter], options: ExportOptions) -> str:
    exporter = exporter_cls(options)
    buf = io.StringIO()
    exporter.write(ledger, buf)
    return buf.getvalue()


def export_ledger(
    source: str | os.PathLike,
    output: str | os.PathLike | None = None,
    *,
    fmt: str | None = None,
    input_format: str | None = None,
    period: str | None = None,
    account: str | None = None,
    running_balance: bool | None = None,
    config: Config | None = None,
    stdout=None,
) -> ExportResult:
    config = config or load_config()
    loaded = load_ledger(
        source, input_format=input_format, config=config, period=period, account=account
    )
    exporter_cls = resolve_exporter(fmt, output, config)
    options = options_from_config(config, running_balance=running_balance)
    text = render_ledger(loaded.ledger, exporter_cls, options)
    if output is None or str(output) == "-":
        (stdout or sys.stdout).write(text)
        destination = "<stdout>"
    else:
        with open(output, "w", encoding=exporter_cls.encoding, newline=exporter_cls.newline) as fh:
            fh.write(text)
        destination = str(output)
    return ExportResult(exporter_cls.format_name, destination, len(loaded.ledger), len(text))


def describe_formats() -> list[dict[str, object]]:
    load_exporters()
    out = []
    for name, cls in exporter_registry:
        out.append(
            {
                "name": name,
                "aliases": exporter_registry.aliases_of(name),
                "extensions": exporter_registry.extensions_of(name),
                "description": cls.description,
            }
        )
    return out
