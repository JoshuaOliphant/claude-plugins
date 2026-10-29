import csv
import os
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from stockline.adapters.store import MemoryStore
from stockline.bootstrap import build_app
from stockline.utils.timeutil import FixedClock

TREE = Path(__file__).resolve().parents[1]
ACME_HEADER = ["Item #", "Description", "Vendor Part", "Cat", "UOM", "Pack", "Unit Cost"]
CATS = ["FAST", "SCRW", "ANCH", "ADH", "TOOL", "PPE", "GLOV", "SIGN", "CLEAN"]


class CountingStore(MemoryStore):
    """Counts every record the store hands back to a caller."""

    def __init__(self):
        super().__init__()
        self.reads = 0

    def get(self, namespace, key):
        self.reads += 1
        return super().get(namespace, key)

    def scan(self, namespace):
        for item in super().scan(namespace):
            self.reads += 1
            yield item


def write_feed(path, n, cost_offset):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(ACME_HEADER)
        for i in range(n):
            w.writerow([
                f"AC-{100000 + i}",
                f"widget model {i}",
                f"ACX {500000 + i}",
                CATS[i % len(CATS)],
                "EA",
                "1",
                f"{2 + (i % 50) * 0.5 + cost_offset:.2f}",
            ])
    return path


def make_app(store=None):
    clock = FixedClock(datetime(2026, 10, 28, 2, 0, tzinfo=timezone.utc))
    return build_app(store=store if store is not None else MemoryStore(), clock=clock)


def nightly_reads(tmp_path, n):
    store = CountingStore()
    app = make_app(store)
    seed = app.importer.import_file(write_feed(tmp_path / f"acme_seed_{n}.csv", n, 0), supplier="ACME")
    assert seed.created == n
    store.reads = 0
    report = app.importer.import_file(write_feed(tmp_path / f"acme_night_{n}.csv", n, 1), supplier="ACME")
    assert report.updated == n
    assert report.rejected == 0
    return store.reads


def test_nightly_import_store_work_scales_linearly(tmp_path):
    small = nightly_reads(tmp_path, 400)
    large = nightly_reads(tmp_path, 800)
    assert large <= 3 * small + 200, (small, large)
    assert large <= 30 * 800, (small, large)


def test_import_updates_prices_and_journal(tmp_path):
    app = make_app()
    app.importer.import_file(write_feed(tmp_path / "acme_a.csv", 30, 0), supplier="ACME")
    report = app.importer.import_file(write_feed(tmp_path / "acme_b.csv", 30, 1), supplier="ACME")
    assert (report.created, report.updated, report.unchanged) == (0, 30, 0)
    p = app.catalog.lookup("AC-100003")
    assert p.cost == Decimal("4.50")
    # hardware.adhesives: hardware markup 45%, min margin 30% -> 6.43 -> 6.99
    assert p.price == Decimal("6.99")
    kinds = [c.kind for c in app.journal.history("AC-100003")]
    assert kinds == ["created", "updated"]
    again = app.importer.import_file(write_feed(tmp_path / "acme_c.csv", 30, 1), supplier="ACME")
    assert (again.created, again.updated, again.unchanged) == (0, 0, 30)


def test_full_feed_discontinues_missing(tmp_path):
    app = make_app()
    app.importer.import_file(write_feed(tmp_path / "acme_a.csv", 20, 0), supplier="ACME")
    report = app.importer.import_file(write_feed(tmp_path / "acme_b.csv", 15, 0),
                                      supplier="ACME", full_feed=True)
    assert report.discontinued == 5
    assert app.catalog.lookup("AC-100019").status == "discontinued"
    assert app.catalog.lookup("AC-100000").status == "active"


def test_cli_import_and_show(tmp_path):
    db = tmp_path / "cat.json"
    env = dict(os.environ, PYTHONPATH=str(TREE))
    env.pop("STOCKLINE_DB", None)
    cmd = [sys.executable, "-m", "stockline", "--db", str(db)]
    for feed in ("acme_2026-10-26.csv", "acme_2026-10-27.csv", "northwind_2026-10-27.jsonl"):
        out = subprocess.run(cmd + ["import", "--quiet", str(TREE / "samples" / feed)],
                             capture_output=True, text=True, env=env, cwd=tmp_path)
        assert out.returncode == 0, out.stderr
    assert "0 created, 13 updated" in out.stdout or "20 created" in out.stdout
    show = subprocess.run(cmd + ["show", "AC-1003"], capture_output=True, text=True, env=env, cwd=tmp_path)
    assert show.returncode == 0, show.stderr
    assert "$6.99" in show.stdout
    runs = subprocess.run(cmd + ["runs"], capture_output=True, text=True, env=env, cwd=tmp_path)
    assert runs.stdout.count("\n") >= 3
