"""Core value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..utils.timeutil import format_iso, parse_iso


class Status(str, Enum):
    OPEN = "open"
    PENDING = "pending"
    ON_HOLD = "on_hold"
    CLOSED = "closed"

    @property
    def is_active(self) -> bool:
        return self is not Status.CLOSED


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

    @property
    def rank(self) -> int:
        return _PRIORITY_RANK[self]


_PRIORITY_RANK = {Priority.LOW: 0, Priority.NORMAL: 1, Priority.HIGH: 2, Priority.URGENT: 3}


class TicketError(ValueError):
    pass


@dataclass(frozen=True)
class Customer:
    id: str
    name: str
    tier: str = "standard"

    @property
    def is_vip(self) -> bool:
        return self.tier in {"enterprise", "vip"}


@dataclass(frozen=True)
class Ticket:
    id: str
    subject: str
    category: str
    status: Status
    priority: Priority
    customer: Customer
    created_at: datetime
    tags: tuple[str, ...] = ()
    assignee: str | None = None

    @classmethod
    def from_record(cls, record: dict) -> "Ticket":
        try:
            customer = record["customer"]
            return cls(
                id=str(record["id"]),
                subject=str(record["subject"]),
                category=str(record.get("category", "general")).lower(),
                status=Status(record["status"]),
                priority=Priority(record.get("priority", "normal")),
                customer=Customer(
                    id=str(customer["id"]),
                    name=str(customer["name"]),
                    tier=str(customer.get("tier", "standard")),
                ),
                created_at=parse_iso(record["created_at"]),
                tags=tuple(sorted(str(t) for t in record.get("tags", ()))),
                assignee=record.get("assignee"),
            )
        except (KeyError, ValueError) as exc:
            raise TicketError(f"bad ticket record {record.get('id')!r}: {exc}") from None

    def to_record(self) -> dict:
        return {
            "id": self.id,
            "subject": self.subject,
            "category": self.category,
            "status": self.status.value,
            "priority": self.priority.value,
            "customer": {"id": self.customer.id, "name": self.customer.name,
                         "tier": self.customer.tier},
            "created_at": format_iso(self.created_at),
            "tags": list(self.tags),
            "assignee": self.assignee,
        }


@dataclass(frozen=True)
class Route:
    channel: str
    template: str = "default"
    rule: str = "fallback"
    suppress: bool = False


@dataclass(frozen=True)
class Notification:
    ticket_id: str
    channel: str
    template: str
    title: str
    body: str
    score: int

    def payload(self) -> dict:
        return {"ticket": self.ticket_id, "title": self.title, "body": self.body,
                "score": self.score}


@dataclass
class Batch:
    number: int
    channel: str
    endpoint: str
    notifications: list[Notification] = field(default_factory=list)

    @property
    def size(self) -> int:
        return len(self.notifications)

    @property
    def ticket_ids(self) -> list[str]:
        return [n.ticket_id for n in self.notifications]

    def envelope(self, service: str) -> dict:
        return {
            "service": service,
            "batch": self.number,
            "channel": self.channel,
            "count": self.size,
            "items": [n.payload() for n in self.notifications],
        }


@dataclass
class DeliveryResult:
    batch: Batch
    ok: bool
    attempts: int
    detail: str = ""
