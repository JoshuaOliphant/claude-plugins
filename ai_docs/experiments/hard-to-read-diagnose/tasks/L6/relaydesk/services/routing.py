"""Decide which channel (and template) a ticket's notification goes to.

Rules live in ``data/routing.toml``.  A ``[defaults]`` table supplies values
every rule inherits unless it sets its own; the first matching rule wins and
``[fallback]`` catches everything else.
"""

from __future__ import annotations

import tomllib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from ..domain.models import Route, Ticket

_RULE_KEYS = {"name", "categories", "priorities", "tiers", "tags", "channel",
              "template", "suppress"}


class RoutingError(ValueError):
    pass


@dataclass(frozen=True)
class Rule:
    name: str
    channel: str
    template: str = "default"
    suppress: bool = False
    categories: frozenset[str] = field(default_factory=frozenset)
    priorities: frozenset[str] = field(default_factory=frozenset)
    tiers: frozenset[str] = field(default_factory=frozenset)
    tags: frozenset[str] = field(default_factory=frozenset)

    def matches(self, ticket: Ticket) -> bool:
        if self.categories and ticket.category not in self.categories:
            return False
        if self.priorities and ticket.priority.value not in self.priorities:
            return False
        if self.tiers and ticket.customer.tier not in self.tiers:
            return False
        if self.tags and not self.tags.intersection(ticket.tags):
            return False
        return True

    def route(self) -> Route:
        return Route(channel=self.channel, template=self.template, rule=self.name,
                     suppress=self.suppress)


def _rule_from_table(table: dict, defaults: dict, index: int) -> Rule:
    unknown = set(table) - _RULE_KEYS
    if unknown:
        raise RoutingError(f"rule #{index}: unknown key(s) {', '.join(sorted(unknown))}")
    merged = {**defaults, **table}
    if "channel" not in merged:
        raise RoutingError(f"rule #{index}: no channel")
    return Rule(
        name=str(merged.get("name", f"rule-{index}")),
        channel=str(merged["channel"]),
        template=str(merged.get("template", "default")),
        suppress=bool(merged.get("suppress", False)),
        categories=frozenset(merged.get("categories", ())),
        priorities=frozenset(merged.get("priorities", ())),
        tiers=frozenset(merged.get("tiers", ())),
        tags=frozenset(merged.get("tags", ())),
    )


class Router:
    def __init__(self, rules: list[Rule], fallback: Rule, include_closed: bool = False):
        self.rules = rules
        self.fallback = fallback
        self.include_closed = include_closed
        self.stats: Counter[str] = Counter()

    @classmethod
    def from_file(cls, path: Path, include_closed: bool = False) -> "Router":
        with path.open("rb") as fh:
            data = tomllib.load(fh)
        defaults = dict(data.get("defaults", {}))
        rules = [_rule_from_table(t, defaults, i)
                 for i, t in enumerate(data.get("rule", []), start=1)]
        fallback_table = {"name": "fallback", **data.get("fallback", {})}
        fallback = _rule_from_table(fallback_table, defaults, 0)
        return cls(rules, fallback, include_closed)

    def route(self, ticket: Ticket) -> Route | None:
        if not ticket.status.is_active and not self.include_closed:
            self.stats["skipped:closed"] += 1
            return None
        for rule in self.rules:
            if rule.matches(ticket):
                route = rule.route()
                break
        else:
            route = self.fallback.route()
        if route.suppress:
            self.stats[f"suppressed:{route.rule}"] += 1
            return None
        self.stats[f"routed:{route.channel}"] += 1
        return route

    def route_all(self, tickets: list[Ticket]) -> list[tuple[Ticket, Route]]:
        routed = []
        for ticket in tickets:
            route = self.route(ticket)
            if route is not None:
                routed.append((ticket, route))
        return routed
