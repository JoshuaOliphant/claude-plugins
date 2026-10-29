# ABOUTME: One known-good fix per task, applied to a copy of the tree to prove each hidden test suite can go green.
# ABOUTME: Usage: reference_fixes.py <task> <tree>; edits <tree> in place. Not shown to the agents.
import re
import sys
from pathlib import Path

task, tree = sys.argv[1], Path(sys.argv[2])


def sub(path, old, new):
    p = tree / path
    s = p.read_text()
    assert old in s, (path, old)
    p.write_text(s.replace(old, new, 1))


FIXES = {
    "h1": lambda: (
        sub("shop/promotions.py", "line[\"item\"].price_cents = round(line[\"item\"].price_cents * (100 - percent) / 100)",
            "line[\"item\"] = __import__('dataclasses').replace(line[\"item\"], price_cents=round(line[\"item\"].price_cents * (100 - percent) / 100))")),
    "h2": lambda: sub("report/config.py", "rounding: int = field(default=2, compare=False)", "rounding: int = 2"),
    "h3": lambda: sub("ledger/handlers.py", 'ev["payload"].get("orig_currency", "USD")', 'ev["payload"].get("orig_currency", ev["payload"].get("currency", "USD"))'),
    "h4": lambda: (tree / "data/prices.csv").write_text((tree / "data/prices.csv").read_text().replace("С", "C")),
    "h5": lambda: sub("billing/money.py", "int(amount * 100)", "round(amount * 100)"),
    "h6": lambda: sub("board/ranking.py", "key=lambda e: e.score, reverse=True", "key=lambda e: (-e.score, e.player)"),
    "h7": lambda: sub("cron/jobs.py", "return last_run_utc + timedelta(seconds=parse_every(self.every))",
                      "secs = parse_every(self.every)\n        if secs % 86400:\n            return last_run_utc + timedelta(seconds=secs)\n        zone = ZoneInfo(self.tz)\n        local = last_run_utc.astimezone(zone)\n        return (local.replace(tzinfo=None) + timedelta(seconds=secs)).replace(tzinfo=zone).astimezone(timezone.utc)"),
    "h8": lambda: sub("apiclient/config.py", "cfg = dict(DEFAULTS)", "cfg = __import__('copy').deepcopy(DEFAULTS)"),
    "h9": lambda: sub("exporter/pipeline.py", "    rows = normalise(fetch_rows(n))\n    shown = preview_lines(rows) if preview else []",
                      "    rows = list(normalise(fetch_rows(n)))\n    shown = preview_lines(iter(rows)) if preview else []"),
    "h10": lambda: sub("settings/loader.py", 'glob.glob(os.path.join(conf_d, "*.json"))', 'sorted(glob.glob(os.path.join(conf_d, "*.json")))'),
}
FIXES[task]()
