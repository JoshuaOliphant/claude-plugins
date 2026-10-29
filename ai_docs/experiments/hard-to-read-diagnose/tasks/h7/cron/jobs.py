from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .spec import parse_every


@dataclass
class Job:
    name: str
    every: str
    tz: str
    first_run_local: str  # "2026-03-05 06:00"

    def first_run(self):
        local = datetime.fromisoformat(self.first_run_local).replace(tzinfo=ZoneInfo(self.tz))
        return local.astimezone(timezone.utc)

    def next_run(self, last_run_utc):
        return last_run_utc + timedelta(seconds=parse_every(self.every))


def upcoming(job, count):
    runs, t = [], job.first_run()
    for _ in range(count):
        runs.append(t)
        t = job.next_run(t)
    return runs


def local_times(job, count):
    zone = ZoneInfo(job.tz)
    return [r.astimezone(zone).strftime("%Y-%m-%d %H:%M") for r in upcoming(job, count)]
