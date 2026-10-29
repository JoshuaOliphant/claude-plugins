"""Human and machine readable summaries of a run."""

from __future__ import annotations

import json
from collections import Counter

from .domain.models import Ticket
from .services.dispatcher import RunReport
from .settings import Settings
from .utils import text


def batches_json(report: RunReport) -> list[str]:
    lines = []
    for result in report.results:
        batch = result.batch
        lines.append(json.dumps({
            "batch": batch.number,
            "channel": batch.channel,
            "endpoint": batch.endpoint,
            "size": batch.size,
            "ok": result.ok,
            "attempts": result.attempts,
            "tickets": batch.ticket_ids,
        }, sort_keys=True))
    return lines


def summary(report: RunReport, dry_run: bool) -> str:
    rows = [[str(r.batch.number), r.batch.channel, str(r.batch.size),
             "ok" if r.ok else "FAILED", r.detail] for r in report.results]
    head = (f"{report.loaded} ticket(s) loaded, {report.rejected} rejected, "
            f"{report.already_sent} already sent, {report.routed} routed")
    verb = "would deliver" if dry_run else "delivered"
    tail = f"{verb} {report.delivered} notification(s) in {len(report.results)} batch(es)"
    if report.failed:
        tail += f"; {len(report.failed)} batch(es) failed"
    parts = [head]
    if rows:
        parts.append(text.table(rows, ["batch", "channel", "size", "status", "detail"]))
    parts.append(tail)
    return "\n".join(parts)


def settings_table(settings: Settings) -> str:
    rows = [[key, str(value)] for key, value in sorted(settings.as_dict().items())]
    return text.table(rows, ["setting", "value"])


def ticket_stats(tickets: list[Ticket]) -> str:
    by_status = Counter(t.status.value for t in tickets)
    by_category = Counter(t.category for t in tickets)
    by_priority = Counter(t.priority.value for t in tickets)
    lines = [f"{len(tickets)} ticket(s)"]
    for title, counter in (("status", by_status), ("category", by_category),
                           ("priority", by_priority)):
        rendered = ", ".join(f"{k}={v}" for k, v in sorted(counter.items()))
        lines.append(f"  {title}: {rendered}")
    return "\n".join(lines)
