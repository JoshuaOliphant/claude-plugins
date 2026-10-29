"""Customers known to the store."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

TIERS = ("standard", "silver", "gold")


@dataclass
class Customer:
    customer_id: str
    name: str
    email: str
    tier: str = "standard"
    region: str = "WA"
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.tier not in TIERS:
            raise ValueError(f"{self.customer_id}: unknown tier {self.tier!r}")

    @property
    def first_name(self) -> str:
        return self.name.split()[0] if self.name else ""

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Customer":
        return cls(
            customer_id=data["customer_id"],
            name=data["name"],
            email=data["email"],
            tier=data.get("tier", "standard"),
            region=data.get("region", "WA"),
            tags=list(data.get("tags", [])),
        )
