"""Integer-cent money arithmetic.

All prices in basketry are integer cents.  Rates are expressed in basis
points (1 bp = 0.01 %) and rounded half-up so totals are reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass


def apply_bps(cents: int, bps: int) -> int:
    """Return ``cents * bps / 10_000`` rounded half-up to the nearest cent."""
    if cents < 0:
        return -apply_bps(-cents, bps)
    numerator = cents * bps
    whole, remainder = divmod(numerator, 10_000)
    return whole + (1 if remainder * 2 >= 10_000 else 0)


def allocate(total: int, weights: list[int]) -> list[int]:
    """Split ``total`` cents proportionally to ``weights`` without losing cents.

    The remainder after flooring is handed out to the largest fractional
    shares first (ties broken by position) so the parts always sum to total.
    """
    if not weights:
        return []
    weight_sum = sum(weights)
    if weight_sum == 0:
        return [0] * len(weights)
    shares = [total * w // weight_sum for w in weights]
    remainders = [(total * w % weight_sum, -i) for i, w in enumerate(weights)]
    leftover = total - sum(shares)
    for _, neg_index in sorted(remainders, reverse=True)[:leftover]:
        shares[-neg_index] += 1
    return shares


@dataclass(frozen=True, order=True)
class Money:
    cents: int
    currency: str = "USD"

    def __add__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.cents + other.cents, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.cents - other.cents, self.currency)

    def __neg__(self) -> "Money":
        return Money(-self.cents, self.currency)

    def times(self, quantity: int) -> "Money":
        return Money(self.cents * quantity, self.currency)

    def percent_bps(self, bps: int) -> "Money":
        return Money(apply_bps(self.cents, bps), self.currency)

    def _check(self, other: "Money") -> None:
        if other.currency != self.currency:
            raise ValueError(f"currency mismatch: {self.currency} vs {other.currency}")

    @classmethod
    def zero(cls, currency: str = "USD") -> "Money":
        return cls(0, currency)
