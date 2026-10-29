"""Turn a routed ticket into a :class:`Notification`."""

from __future__ import annotations

from datetime import datetime

from ..domain import priority
from ..domain.models import Notification, Route, Ticket
from ..utils import text
from ..utils.timeutil import format_iso, humanize
from .templates import TemplateStore


class Formatter:
    def __init__(self, store: TemplateStore, max_summary: int, now: datetime):
        self.store = store
        self.max_summary = max_summary
        self.now = now

    def fields(self, ticket: Ticket) -> dict[str, str]:
        return {
            "id": ticket.id,
            "subject": text.truncate(ticket.subject, self.max_summary),
            "category": ticket.category,
            "priority": ticket.priority.value,
            "PRIORITY": ticket.priority.value.upper(),
            "status": ticket.status.value.replace("_", " "),
            "customer": ticket.customer.name,
            "tier": ticket.customer.tier,
            "assignee": ticket.assignee or "unassigned",
            "created": format_iso(ticket.created_at),
            "age": humanize(self.now - ticket.created_at),
            "tags": ", ".join(ticket.tags) or "-",
        }

    def render(self, ticket: Ticket, route: Route) -> Notification:
        template = self.store.get(route.template)
        title, body = template.render(self.fields(ticket))
        return Notification(
            ticket_id=ticket.id,
            channel=route.channel,
            template=route.template,
            title=title,
            body=body,
            score=priority.score(ticket, self.now),
        )

    def render_all(self, routed: list[tuple[Ticket, Route]]) -> list[Notification]:
        return [self.render(ticket, route) for ticket, route in routed]
