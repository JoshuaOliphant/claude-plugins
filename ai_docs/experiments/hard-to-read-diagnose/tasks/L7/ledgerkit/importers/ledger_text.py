"""The native plain-text ledger format.

One transaction per line, fields separated by two or more spaces or by
``|``::

    2026-03-02 | Corner Bakery | checking | food:bakery | -6.40 | croissants #weekend

Lines starting with ``#`` or ``;`` are comments. A ``!currency EUR``
directive changes the currency for the remainder of the file.
"""

from __future__ import annotations

import re

from ledgerkit.importers.base import Importer, ImportError_, register_importer

_SPLIT_RE = re.compile(r"\s*\|\s*|\s{2,}")
_TAG_RE = re.compile(r"#([\w:-]+)")


@register_importer("ledger", extensions=(".ledger", ".txt"))
class LedgerTextImporter(Importer):
    def parse(self, text, source, report):
        currency = self.currency
        for lineno, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            if not line or line[0] in "#;":
                continue
            if line.startswith("!"):
                directive, _, arg = line[1:].partition(" ")
                if directive == "currency" and arg.strip():
                    currency = arg.strip().upper()
                    if currency != self.currency:
                        raise ImportError_(source, lineno, f"ledger currency is {self.currency}, not {currency}")
                    continue
                raise ImportError_(source, lineno, f"unknown directive {directive!r}")
            parts = [p for p in _SPLIT_RE.split(line)]
            if len(parts) < 5:
                if self.strict:
                    raise ImportError_(source, lineno, "expected at least 5 fields")
                report.skipped += 1
                continue
            date, payee, account, category, amount = parts[:5]
            memo = " ".join(parts[5:])
            tags = tuple(_TAG_RE.findall(memo))
            memo = _TAG_RE.sub("", memo).strip()
            txn = self.build(
                source,
                lineno,
                report,
                date=date,
                payee=payee,
                account=account,
                category=category,
                amount=amount,
                currency=currency,
                memo=memo,
                tags=tags,
            )
            if txn is not None:
                yield txn
