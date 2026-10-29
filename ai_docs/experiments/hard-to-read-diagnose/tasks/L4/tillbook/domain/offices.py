"""Office registry.

Each office reports in its own calendar: a "day" for the Mumbai store is
midnight to midnight India Standard Time, regardless of where the reporting
server happens to run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from tillbook.utils.timeconv import UTC


class UnknownOffice(KeyError):
    def __str__(self) -> str:
        return f"unknown office {self.args[0]!r}"


@dataclass(frozen=True)
class Office:
    code: str
    name: str
    timezone: str
    currency: str
    tills: tuple[str, ...]
    opens: time
    closes: time

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def day_bounds(self, day: date) -> tuple[datetime, datetime]:
        """Return ``[start, end)`` of the office-local calendar day, in UTC."""
        start = datetime.combine(day, time.min, tzinfo=self.tz)
        end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=self.tz)
        return start.astimezone(UTC), end.astimezone(UTC)

    def local(self, moment: datetime) -> datetime:
        return moment.astimezone(self.tz)

    def is_trading_time(self, moment: datetime) -> bool:
        wall = self.local(moment).time()
        if self.opens <= self.closes:
            return self.opens <= wall < self.closes
        return wall >= self.opens or wall < self.closes


class OfficeRegistry:
    def __init__(self, offices: list[Office]) -> None:
        self._by_code = {office.code: office for office in offices}

    @classmethod
    def load(cls, path: Path) -> "OfficeRegistry":
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        offices = []
        for raw in payload["offices"]:
            try:
                ZoneInfo(raw["timezone"])
            except ZoneInfoNotFoundError as exc:
                raise ValueError(f"office {raw['code']}: bad timezone {raw['timezone']!r}") from exc
            offices.append(
                Office(
                    code=raw["code"].upper(),
                    name=raw["name"],
                    timezone=raw["timezone"],
                    currency=raw["currency"].upper(),
                    tills=tuple(raw.get("tills", [])),
                    opens=time.fromisoformat(raw.get("opens", "00:00")),
                    closes=time.fromisoformat(raw.get("closes", "23:59")),
                )
            )
        return cls(offices)

    def get(self, code: str) -> Office:
        try:
            return self._by_code[code.upper()]
        except KeyError:
            raise UnknownOffice(code) from None

    def __contains__(self, code: str) -> bool:
        return code.upper() in self._by_code

    def __iter__(self):
        return iter(sorted(self._by_code.values(), key=lambda office: office.code))

    def codes(self) -> list[str]:
        return sorted(self._by_code)
