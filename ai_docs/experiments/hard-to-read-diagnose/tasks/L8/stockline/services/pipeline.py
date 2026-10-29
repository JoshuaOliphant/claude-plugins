"""Row pipeline: map columns, drop repeats, normalise, validate, price.

Each stage is a callable taking and returning a ``FeedRow``.  A stage
signals rejection by appending to ``row.errors``; later stages are then
skipped for that row.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Iterator

from stockline.domain.errors import FeedFormatError
from stockline.domain.models import FeedRow
from stockline.services.normalize import ColumnMapper
from stockline.utils.dedupe import RecentWindow

Stage = Callable[[FeedRow], FeedRow]

ACCEPTED = "accepted"
REJECTED = "rejected"
DUPLICATE = "duplicate"


@dataclass
class Outcome:
    status: str
    row: FeedRow


def _fingerprint(raw: dict) -> tuple:
    return tuple(sorted((k, str(v)) for k, v in raw.items()))


class RowPipeline:
    def __init__(self, mapper: ColumnMapper, stages: list[Stage], dedupe_window: int = 64):
        self.mapper = mapper
        self.stages = list(stages)
        self.window = RecentWindow(dedupe_window)
        self._header_checked = False

    def _check_header(self, raw: dict, line_no: int) -> list[str]:
        self._header_checked = True
        return self.mapper.check_header(raw)

    def process(self, records: Iterable[tuple[int, dict]]) -> Iterator[Outcome]:
        for line_no, raw in records:
            if not self._header_checked:
                missing = self._check_header(raw, line_no)
                if missing:
                    raise FeedFormatError(
                        self.mapper.supplier.code,
                        f"feed is missing column(s): {', '.join(missing)}",
                    )
            row = self.mapper(line_no, raw)
            if self.window.seen(_fingerprint(raw)):
                yield Outcome(DUPLICATE, row)
                continue
            for stage in self.stages:
                row = stage(row)
                if not row.ok:
                    break
            yield Outcome(ACCEPTED if row.ok else REJECTED, row)
