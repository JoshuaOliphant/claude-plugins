"""In-process event bus.

The catalog publishes domain events; the journal, the run tracker and
optional integrations subscribe.  Handlers run synchronously in
subscription order, so a handler that raises aborts the current import.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable

from stockline.domain.models import ImportRun, Product


@dataclass(frozen=True)
class ProductCreated:
    product: Product
    run_id: str


@dataclass(frozen=True)
class ProductUpdated:
    product: Product
    changes: dict
    run_id: str


@dataclass(frozen=True)
class ProductDiscontinued:
    product: Product
    run_id: str


@dataclass(frozen=True)
class ImportFinished:
    run: ImportRun
    rejects: list = field(default_factory=list)


Handler = Callable[[object], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type, list[Handler]] = defaultdict(list)
        self.published = 0

    def subscribe(self, event_type: type, handler: Handler) -> Callable[[], None]:
        self._handlers[event_type].append(handler)

        def unsubscribe() -> None:
            if handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)

        return unsubscribe

    def publish(self, event: object) -> None:
        self.published += 1
        for handler in list(self._handlers.get(type(event), ())):
            handler(event)

    def handler_count(self, event_type: type) -> int:
        return len(self._handlers.get(event_type, ()))
