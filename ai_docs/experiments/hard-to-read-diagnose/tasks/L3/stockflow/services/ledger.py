"""Posting validated movements to the stock repository."""

from __future__ import annotations

from dataclasses import dataclass

from stockflow.adapters.repository import InMemoryStockRepository
from stockflow.domain.models import Movement, MovementKind
from stockflow.services.metrics import Metrics


@dataclass(frozen=True)
class PostingOutcome:
    movement: Movement
    posted: bool

    @property
    def duplicate(self) -> bool:
        return not self.posted


class Ledger:
    def __init__(self, repository: InMemoryStockRepository, metrics: Metrics) -> None:
        self.repository = repository
        self.metrics = metrics

    def post(self, movement: Movement) -> PostingOutcome:
        posted = self.repository.record(movement)
        if posted:
            self.metrics.incr("movements.posted")
            self.metrics.incr(f"movements.{movement.kind.value.lower()}")
        else:
            self.metrics.incr("movements.duplicate")
        return PostingOutcome(movement, posted)

    def post_transfer(self, out_leg: Movement, in_leg: Movement) -> tuple[PostingOutcome, PostingOutcome]:
        """Post both legs of an inter-warehouse transfer."""
        if out_leg.kind is not MovementKind.TRANSFER_OUT or in_leg.kind is not MovementKind.TRANSFER_IN:
            raise ValueError("transfer legs must be TRANSFER_OUT then TRANSFER_IN")
        if out_leg.sku != in_leg.sku or out_leg.quantity != in_leg.quantity:
            raise ValueError("transfer legs must move the same SKU and quantity")
        return self.post(out_leg), self.post(in_leg)
