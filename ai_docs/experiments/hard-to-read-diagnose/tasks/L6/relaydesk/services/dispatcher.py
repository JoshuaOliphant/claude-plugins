"""End-to-end pipeline: tickets -> routes -> notifications -> batches -> transport."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from ..adapters.outbox import MemoryTransport, OutboxTransport
from ..adapters.state import DeliveryState
from ..adapters.ticket_source import TicketSource
from ..adapters.webhook import WebhookError, WebhookTransport
from ..domain import priority
from ..domain.models import Batch, DeliveryResult
from ..settings import Settings
from ..utils.timeutil import ManualClock, MonotonicClock
from .batcher import Batcher
from .formatter import Formatter
from .ratelimit import TokenBucket
from .retry import RetryPolicy, TransientError
from .routing import Router
from .templates import TemplateStore

log = logging.getLogger(__name__)


@dataclass
class RunReport:
    loaded: int = 0
    rejected: int = 0
    already_sent: int = 0
    routed: int = 0
    batches: list[Batch] = field(default_factory=list)
    results: list[DeliveryResult] = field(default_factory=list)
    router_stats: dict[str, int] = field(default_factory=dict)
    throttled: int = 0

    @property
    def delivered(self) -> int:
        return sum(r.batch.size for r in self.results if r.ok)

    @property
    def failed(self) -> list[DeliveryResult]:
        return [r for r in self.results if not r.ok]


def make_transport(settings: Settings, dry_run: bool):
    service = settings.service.name
    if dry_run:
        return MemoryTransport(service)
    kind = settings.delivery.transport
    if kind == "outbox":
        return OutboxTransport(settings.path("delivery.outbox_dir"), service)
    if kind == "webhook":
        return WebhookTransport(service, settings.delivery.timeout,
                                settings.delivery.verify_tls)
    raise ValueError(f"unknown transport {kind!r}")


class Dispatcher:
    def __init__(self, settings: Settings, now: datetime, dry_run: bool = False,
                 transport=None):
        self.settings = settings
        self.now = now
        self.dry_run = dry_run
        self.transport = transport or make_transport(settings, dry_run)
        self.clock = ManualClock() if dry_run else MonotonicClock()
        self.state = DeliveryState(settings.path("state.db"), readonly=dry_run)

    def _router(self) -> Router:
        return Router.from_file(self.settings.path("routing.rules_file"),
                                include_closed=self.settings.routing.include_closed)

    def _formatter(self) -> Formatter:
        store = TemplateStore(self.settings.path("templates.dir"))
        return Formatter(store, self.settings.templates.max_summary, self.now)

    def _batcher(self) -> Batcher:
        delivery = self.settings.delivery
        return Batcher(delivery.batch_size, delivery.endpoint)

    def plan(self, report: RunReport) -> list[Batch]:
        source = TicketSource(self.settings.path("sources.tickets"))
        tickets = source.load()
        report.loaded = len(tickets)
        report.rejected = len(source.rejected)

        sent = self.state.delivered_ids()
        fresh = [t for t in tickets if t.id not in sent]
        report.already_sent = len(tickets) - len(fresh)

        router = self._router()
        routed = router.route_all(priority.order(fresh, self.now))
        report.router_stats = dict(router.stats)
        report.routed = len(routed)

        notifications = self._formatter().render_all(routed)
        return self._batcher().build(notifications)

    def run(self) -> RunReport:
        report = RunReport()
        report.batches = self.plan(report)
        rate = self.settings.rate
        retry = self.settings.retry
        limiter = TokenBucket(rate.per_minute, rate.burst, self.clock)
        policy = RetryPolicy(retry.attempts, retry.backoff, retry.max_backoff, self.clock)
        for batch in report.batches:
            limiter.acquire()
            try:
                detail, attempts = policy.call(lambda b=batch: self.transport.deliver(b))
            except (TransientError, WebhookError) as exc:
                log.error("batch %d to %s failed: %s", batch.number, batch.channel, exc)
                report.results.append(DeliveryResult(batch, False, retry.attempts, str(exc)))
                continue
            self.state.mark(batch.ticket_ids, batch.channel, batch.number)
            report.results.append(DeliveryResult(batch, True, attempts, detail))
        report.throttled = limiter.waits
        self.state.close()
        return report
