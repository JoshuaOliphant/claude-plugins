"""Discounts: loyalty tiers, bulk category discounts and coupon codes."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from ..config import Settings
from ..domain.money import apply_bps
from ..domain.order import Order
from ..domain.summary import Adjustment
from .pricing import PricedOrder


@dataclass(frozen=True)
class Coupon:
    code: str
    kind: str
    value: int
    min_subtotal_cents: int = 0
    categories: frozenset[str] = frozenset()

    def applies_to(self, category: str) -> bool:
        return not self.categories or category in self.categories


@dataclass(frozen=True)
class BulkRule:
    category: str
    min_quantity: int
    discount_bps: int


@dataclass(frozen=True)
class PromotionBook:
    coupons: dict[str, Coupon]
    bulk: tuple[BulkRule, ...]

    @classmethod
    def load(cls, path: Path) -> "PromotionBook":
        with Path(path).open(encoding="utf-8") as fh:
            raw = json.load(fh)
        coupons = {
            entry["code"].upper(): Coupon(
                code=entry["code"].upper(),
                kind=entry["kind"],
                value=int(entry["value"]),
                min_subtotal_cents=int(entry.get("min_subtotal_cents", 0)),
                categories=frozenset(entry.get("categories", [])),
            )
            for entry in raw.get("coupons", [])
        }
        bulk = tuple(BulkRule(**entry) for entry in raw.get("bulk", []))
        return cls(coupons=coupons, bulk=bulk)


Rule = Callable[["PromotionEngine", Order, PricedOrder], list[Adjustment]]


def tier_rule(engine: "PromotionEngine", order: Order, priced: PricedOrder) -> list[Adjustment]:
    bps = engine.settings.tier_discount(order.customer.tier)
    if not bps:
        return []
    amount = apply_bps(priced.subtotal_cents, bps)
    if not amount:
        return []
    return [
        Adjustment(
            code=f"TIER-{order.customer.tier.upper()}",
            description=f"{order.customer.tier.capitalize()} member discount",
            amount_cents=-amount,
        )
    ]


def bulk_rule(engine: "PromotionEngine", order: Order, priced: PricedOrder) -> list[Adjustment]:
    out: list[Adjustment] = []
    for rule in engine.book.bulk:
        lines = order.lines_in(rule.category)
        if sum(line.quantity for line in lines) < rule.min_quantity:
            continue
        amount = apply_bps(sum(line.total_cents for line in lines), rule.discount_bps)
        if amount:
            out.append(
                Adjustment(
                    code=f"BULK-{rule.category.upper()}",
                    description=f"Bulk {rule.category} discount",
                    amount_cents=-amount,
                )
            )
    return out


def coupon_rule(engine: "PromotionEngine", order: Order, priced: PricedOrder) -> list[Adjustment]:
    out: list[Adjustment] = []
    rejected: list[str] = []
    for code in order.coupons:
        coupon = engine.book.coupons.get(code)
        if coupon is None:
            rejected.append(f"Coupon {code} is not recognised")
            continue
        eligible = sum(
            line.total_cents for line in order.lines if coupon.applies_to(line.category)
        )
        if eligible == 0 or priced.subtotal_cents < coupon.min_subtotal_cents:
            rejected.append(f"Coupon {code} does not apply to this order")
            continue
        if coupon.kind == "percent":
            amount = apply_bps(eligible, coupon.value)
        else:
            amount = min(coupon.value, eligible)
        out.append(Adjustment(code=code, description=f"Coupon {code}", amount_cents=-amount))
    engine.last_rejections = rejected
    return out


class PromotionEngine:
    DEFAULT_RULES: tuple[Rule, ...] = (tier_rule, bulk_rule, coupon_rule)

    def __init__(self, settings: Settings, book: PromotionBook, rules: Iterable[Rule] | None = None):
        self.settings = settings
        self.book = book
        self.rules: list[Rule] = list(rules if rules is not None else self.DEFAULT_RULES)
        self.last_rejections: list[str] = []

    def add_rule(self, rule: Rule) -> None:
        self.rules.append(rule)

    def evaluate(self, order: Order, priced: PricedOrder) -> list[Adjustment]:
        self.last_rejections = []
        adjustments: list[Adjustment] = []
        for rule in self.rules:
            adjustments.extend(rule(self, order, priced))
        total_discount = -sum(a.amount_cents for a in adjustments)
        if total_discount > priced.subtotal_cents:
            overflow = total_discount - priced.subtotal_cents
            last = adjustments[-1]
            adjustments[-1] = Adjustment(last.code, last.description, last.amount_cents + overflow)
        return adjustments
