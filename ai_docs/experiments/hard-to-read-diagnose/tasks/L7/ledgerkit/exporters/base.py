"""Exporter base class.

Concrete exporters subclass :class:`Exporter`, set ``format_name`` and are
registered automatically when their module is imported. Intermediate base
classes set ``abstract = True`` so they are not offered as formats.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import IO

from ledgerkit.models import Ledger, Transaction
from ledgerkit.plugins.registry import Registry

exporter_registry: Registry[type["Exporter"]] = Registry("export format")

ALL_COLUMNS = ("date", "payee", "account", "category", "amount", "currency", "memo", "tags", "id")


@dataclass
class ExportOptions:
    columns: tuple[str, ...] = ("date", "payee", "account", "category", "amount", "currency", "memo")
    date_format: str = ""
    locale: str = "C"
    title: str = "Ledger report"
    running_balance: bool = False
    extra: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        unknown = [c for c in self.columns if c not in ALL_COLUMNS]
        if unknown:
            raise ValueError(f"unknown column(s): {', '.join(unknown)}")


class Exporter:
    abstract = True
    format_name: str = ""
    aliases: tuple[str, ...] = ()
    extensions: tuple[str, ...] = ()
    description: str = ""
    encoding: str = "utf-8"
    newline: str | None = ""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.__dict__.get("abstract", False):
            return
        if not cls.format_name:
            raise TypeError(f"{cls.__name__} must define format_name")
        exporter_registry.register(
            cls.format_name, cls, aliases=cls.aliases, extensions=cls.extensions
        )

    def __init__(self, options: ExportOptions | None = None):
        self.options = options or ExportOptions()

    def render(self, ledger: Ledger) -> str:
        raise NotImplementedError

    def write(self, ledger: Ledger, stream: IO[str]) -> int:
        text = self.render(ledger)
        stream.write(text)
        return len(text)

    def cell(self, txn: Transaction, column: str, balance=None) -> str:
        if column == "date":
            return self.format_date(txn)
        if column == "amount":
            return self.format_amount(txn.amount)
        if column == "currency":
            return txn.amount.currency
        if column == "tags":
            return " ".join(txn.tags)
        if column == "id":
            return txn.txn_id
        return str(getattr(txn, column))

    def format_date(self, txn: Transaction) -> str:
        fmt = self.options.date_format
        return txn.date.strftime(fmt) if fmt else txn.date.isoformat()

    def format_amount(self, money) -> str:
        return money.plain()

    def rows(self, ledger: Ledger):
        if self.options.running_balance:
            for txn, balance in ledger.running_balances():
                yield txn, balance
        else:
            for txn in ledger.sorted():
                yield txn, None
