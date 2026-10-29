"""Read till exports in JSON-lines format."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterator

from tillbook.adapters.codec import DecodeError, decode_till_record
from tillbook.domain.models import Transaction

log = logging.getLogger(__name__)


class JsonlTillSource:
    def __init__(self, paths: list[Path], strict: bool = False) -> None:
        self.paths = sorted(paths)
        self.strict = strict
        self.rejected: list[DecodeError] = []

    @classmethod
    def from_glob(cls, root: Path, pattern: str, strict: bool = False) -> "JsonlTillSource":
        return cls(list(root.glob(pattern)), strict=strict)

    def __iter__(self) -> Iterator[Transaction]:
        for path in self.paths:
            yield from self._read(path)

    def _read(self, path: Path) -> Iterator[Transaction]:
        with path.open(encoding="utf-8") as handle:
            for number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                where = f"{path.name}:{number}"
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    error = DecodeError(f"invalid JSON: {exc.msg}", None, where)
                    if self.strict:
                        raise error from exc
                    self.rejected.append(error)
                    log.warning("skipping %s", error)
                    continue
                try:
                    yield decode_till_record(record, source=where)
                except DecodeError as error:
                    error.where = where
                    if self.strict:
                        raise
                    self.rejected.append(error)
                    log.warning("skipping %s", error)
