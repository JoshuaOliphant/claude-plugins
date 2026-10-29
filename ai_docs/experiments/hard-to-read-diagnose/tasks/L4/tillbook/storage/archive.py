"""Snapshot archive for published reports.

Each ``--archive`` run writes the JSON payload to a file named after the
moment it was produced, so operators can see on the server what was sent
and when. Snapshots older than the retention window are pruned.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_RETENTION_DAYS = 30


class SnapshotArchive:
    def __init__(self, root: Path, retention_days: int = DEFAULT_RETENTION_DAYS) -> None:
        self.root = root
        self.retention_days = retention_days

    def _name(self, kind: str, label: str, stamp: float) -> str:
        wall = time.strftime("%Y%m%d-%H%M%S", time.localtime(stamp))
        safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)
        return f"{kind}-{safe_label}-{wall}.json"

    def write(self, kind: str, label: str, payload: Any, stamp: float | None = None) -> Path:
        stamp = time.time() if stamp is None else stamp
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / self._name(kind, label, stamp)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, path)
        log.info("archived %s", path.name)
        return path

    def cutoff(self, now: datetime | None = None) -> float:
        """Epoch seconds before which snapshots are pruned.

        Retention is counted in whole server-local days: everything from
        before local midnight ``retention_days`` ago is dropped.
        """
        now = now or datetime.now()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        boundary = midnight - timedelta(days=self.retention_days)
        return time.mktime(boundary.timetuple())

    def prune(self, now: datetime | None = None) -> list[Path]:
        if not self.root.exists():
            return []
        limit = self.cutoff(now)
        removed = []
        for path in sorted(self.root.glob("*.json")):
            if path.stat().st_mtime < limit:
                path.unlink()
                removed.append(path)
        if removed:
            log.info("pruned %d snapshots", len(removed))
        return removed

    def list(self, kind: str | None = None) -> list[Path]:
        if not self.root.exists():
            return []
        pattern = f"{kind}-*.json" if kind else "*.json"
        return sorted(self.root.glob(pattern))
