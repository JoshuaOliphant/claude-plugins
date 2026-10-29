"""Scoring tickets so the most pressing ones lead each batch."""

from __future__ import annotations

from datetime import datetime, timedelta

from .models import Priority, Ticket

_BASE = {Priority.LOW: 10, Priority.NORMAL: 30, Priority.HIGH: 60, Priority.URGENT: 90}
_CATEGORY_BONUS = {"outage": 15, "security": 20, "billing": 5}
_TAG_BONUS = {"regression": 5, "data-loss": 25, "escalated": 10}


def score(ticket: Ticket, now: datetime) -> int:
    value = _BASE[ticket.priority]
    value += _CATEGORY_BONUS.get(ticket.category, 0)
    value += sum(_TAG_BONUS.get(tag, 0) for tag in ticket.tags)
    if ticket.customer.is_vip:
        value += 10
    waiting = now - ticket.created_at
    if waiting > timedelta(days=3):
        value += 10
    elif waiting > timedelta(days=1):
        value += 5
    return min(value, 150)


def order(tickets: list[Ticket], now: datetime) -> list[Ticket]:
    """Highest score first; ties broken by age (oldest first) then id."""
    return sorted(tickets, key=lambda t: (-score(t, now), t.created_at, t.id))
