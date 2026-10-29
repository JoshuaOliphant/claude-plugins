"""Outbox transport: each batch becomes a JSON file that a separate shipper
process forwards to the webhook.  Also used by ``--dry-run`` in memory."""

from __future__ import annotations

import json
import os
from pathlib import Path

from ..domain.models import Batch
from ..utils import text
from ..utils.paths import ensure_dir
from ..utils.timeutil import stamp


class OutboxTransport:
    name = "outbox"

    def __init__(self, directory: Path, service: str):
        self.directory = directory
        self.service = service
        self.written: list[Path] = []

    def filename(self, batch: Batch) -> str:
        return f"{stamp()}-{batch.number:04d}-{text.slugify(batch.channel)}.json"

    def deliver(self, batch: Batch) -> str:
        ensure_dir(self.directory)
        target = self.directory / self.filename(batch)
        tmp = target.with_suffix(".tmp")
        document = {"endpoint": batch.endpoint, **batch.envelope(self.service)}
        tmp.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, target)
        self.written.append(target)
        return str(target)


class MemoryTransport:
    """Collects envelopes instead of sending them."""

    name = "dry-run"

    def __init__(self, service: str):
        self.service = service
        self.sent: list[dict] = []

    def deliver(self, batch: Batch) -> str:
        self.sent.append({"endpoint": batch.endpoint, **batch.envelope(self.service)})
        return "kept in memory"
