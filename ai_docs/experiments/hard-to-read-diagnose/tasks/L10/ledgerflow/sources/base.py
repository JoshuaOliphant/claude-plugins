"""Source interface.

A source turns some external format into ``RawRecord`` objects. Values stay
as text; parsing and conversion happen in the normaliser so that every source
gets identical rules and error messages.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterator

REQUIRED_FIELDS = ("record_id", "posted", "amount", "currency", "account")


@dataclass(slots=True)
class RawRecord:
    record_id: str
    posted: str
    amount: str
    currency: str
    account: str
    memo: str = ""
    date_format: str | None = None
    line: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def missing(self) -> list[str]:
        return [name for name in REQUIRED_FIELDS if not str(getattr(self, name) or "").strip()]


class Source(ABC):
    kind: str = "abstract"

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def records(self) -> Iterator[RawRecord]:
        """Yield every record of the source, from the beginning, on each call."""

    def describe(self) -> str:
        return f"{self.kind}:{self.name}"

    def close(self) -> None:
        pass

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.name}>"
