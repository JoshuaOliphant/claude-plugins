"""Rule-based categorisation of transaction memos."""

from __future__ import annotations

import functools
import json
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class Rule:
    pattern: str
    category: str
    accounts: frozenset[str] = frozenset()
    min_abs_amount: Decimal | None = None

    def matches(self, memo: str, account: str, amount: Decimal) -> bool:
        if self.accounts and account not in self.accounts:
            return False
        if self.min_abs_amount is not None and abs(amount) < self.min_abs_amount:
            return False
        return _compile(self.pattern).search(memo) is not None


@functools.lru_cache(maxsize=256)
def _compile(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


class Categorizer:
    def __init__(self, rules: list[Rule], default: str = "uncategorized"):
        self.rules = list(rules)
        self.default = default

    def categorize(self, memo: str, account: str, amount: Decimal) -> str:
        for rule in self.rules:
            if rule.matches(memo, account, amount):
                return rule.category
        return self.default

    def categories(self) -> list[str]:
        seen = dict.fromkeys(r.category for r in self.rules)
        seen.setdefault(self.default)
        return list(seen)


def load_categorizer(path: Path) -> Categorizer:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    rules = []
    for entry in raw.get("rules", []):
        _compile(entry["pattern"])  # fail fast on a bad expression
        rules.append(Rule(
            pattern=entry["pattern"],
            category=entry["category"],
            accounts=frozenset(entry.get("accounts", ())),
            min_abs_amount=Decimal(entry["min_abs_amount"]) if "min_abs_amount" in entry else None,
        ))
    return Categorizer(rules, raw.get("default", "uncategorized"))
