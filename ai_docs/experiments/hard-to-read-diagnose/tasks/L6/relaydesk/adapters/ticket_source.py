"""Read tickets from the help-desk's JSON-lines export."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path

from ..domain.models import Ticket, TicketError

log = logging.getLogger(__name__)


class TicketSource:
    def __init__(self, path: Path, strict: bool = False):
        self.path = path
        self.strict = strict
        self.rejected: list[tuple[int, str]] = []

    def records(self) -> Iterator[tuple[int, dict]]:
        with self.path.open(encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                line = line.strip()
                if not line or line.startswith("//"):
                    continue
                try:
                    yield lineno, json.loads(line)
                except json.JSONDecodeError as exc:
                    self._reject(lineno, f"invalid JSON: {exc.msg}")

    def _reject(self, lineno: int, reason: str) -> None:
        if self.strict:
            raise TicketError(f"{self.path}:{lineno}: {reason}")
        log.warning("%s:%d skipped: %s", self.path.name, lineno, reason)
        self.rejected.append((lineno, reason))

    def load(self) -> list[Ticket]:
        tickets: list[Ticket] = []
        seen: set[str] = set()
        for lineno, record in self.records():
            try:
                ticket = Ticket.from_record(record)
            except TicketError as exc:
                self._reject(lineno, str(exc))
                continue
            if ticket.id in seen:
                self._reject(lineno, f"duplicate ticket id {ticket.id}")
                continue
            seen.add(ticket.id)
            tickets.append(ticket)
        return tickets
