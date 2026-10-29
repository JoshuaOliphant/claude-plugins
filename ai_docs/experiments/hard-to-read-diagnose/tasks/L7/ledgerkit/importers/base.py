"""Importer protocol and registration helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

from ledgerkit.models import Ledger, Transaction
from ledgerkit.money import DEFAULT_CURRENCY, MoneyError, parse_amount
from ledgerkit.plugins.registry import Registry
from ledgerkit.utils.dates import DateParseError, parse_date

importer_registry: Registry["Importer"] = Registry("input format")


class ImportError_(ValueError):
    """A record in the input could not be understood."""

    def __init__(self, source: str, line: int, message: str):
        self.source = source
        self.line = line
        super().__init__(f"{source}:{line}: {message}")


@dataclass
class ImportReport:
    source: str
    read: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


class Importer:
    name = ""
    extensions: tuple[str, ...] = ()

    def __init__(self, currency: str = DEFAULT_CURRENCY, strict: bool = True):
        self.currency = currency
        self.strict = strict

    def parse(self, text: str, source: str, report: ImportReport) -> Iterable[Transaction]:
        raise NotImplementedError

    def load(self, text: str, source: str = "<input>") -> tuple[Ledger, ImportReport]:
        report = ImportReport(source)
        ledger = Ledger(currency=self.currency, source=source)
        for txn in self.parse(text, source, report):
            ledger.add(txn)
            report.read += 1
        return ledger, report

    def build(self, source: str, line: int, report: ImportReport, **fields) -> Transaction | None:
        try:
            when = parse_date(fields.pop("date"))
            amount = parse_amount(fields.pop("amount"), fields.pop("currency", None) or self.currency)
        except (DateParseError, MoneyError, KeyError) as exc:
            if self.strict:
                raise ImportError_(source, line, str(exc)) from exc
            report.skipped += 1
            report.errors.append(f"{source}:{line}: {exc}")
            return None
        tags = fields.pop("tags", ()) or ()
        if isinstance(tags, str):
            tags = tuple(t for t in tags.replace(",", " ").split() if t)
        return Transaction(
            date=when,
            payee=(fields.get("payee") or "").strip(),
            account=(fields.get("account") or "default").strip(),
            amount=amount,
            category=(fields.get("category") or "uncategorized").strip(),
            memo=(fields.get("memo") or "").strip(),
            tags=tuple(tags),
            txn_id=(fields.get("id") or "").strip(),
        )


def register_importer(name: str, *, extensions=()) -> Callable[[type[Importer]], type[Importer]]:
    def decorator(cls: type[Importer]) -> type[Importer]:
        cls.name = name
        cls.extensions = tuple(extensions)
        importer_registry.register(name, cls, extensions=extensions)
        return cls

    return decorator
