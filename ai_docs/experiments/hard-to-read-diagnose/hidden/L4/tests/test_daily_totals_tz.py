import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

TREE = Path(__file__).resolve().parent.parent

SERVER_TZS = ["UTC", "Asia/Kolkata", "America/Los_Angeles", "Asia/Tokyo"]

KEYS = ("date", "sales", "refunds", "voids", "gross", "refunded", "net", "by_tender")

EXPECTED = {
    ("BOM", "2026-03-13", "2026-03-15"): [
        {"date": "2026-03-13", "sales": 24, "refunds": 1, "voids": 3, "gross": "58152.00",
         "refunded": "349.00", "net": "57803.00",
         "by_tender": {"card": "13488.00", "cash": "15138.00", "upi": "16786.00", "wallet": "12391.00"}},
        {"date": "2026-03-14", "sales": 24, "refunds": 1, "voids": 1, "gross": "65690.00",
         "refunded": "2848.00", "net": "62842.00",
         "by_tender": {"card": "17182.00", "cash": "14539.00", "upi": "10389.00", "wallet": "20732.00"}},
        {"date": "2026-03-15", "sales": 25, "refunds": 2, "voids": 1, "gross": "64890.00",
         "refunded": "3298.00", "net": "61592.00",
         "by_tender": {"card": "7191.00", "cash": "13986.00", "upi": "21377.00", "wallet": "19038.00"}},
    ],
    ("LAX", "2026-03-13", "2026-03-14"): [
        {"date": "2026-03-13", "sales": 26, "refunds": 1, "voids": 1, "gross": "2242.00",
         "refunded": "138.00", "net": "2104.00",
         "by_tender": {"card": "1130.00", "cash": "502.00", "wallet": "472.00"}},
        {"date": "2026-03-14", "sales": 31, "refunds": 4, "voids": 2, "gross": "2938.00",
         "refunded": "210.00", "net": "2728.00",
         "by_tender": {"card": "1928.00", "cash": "446.00", "wallet": "354.00"}},
    ],
}


def run_daily(office, first, last, tz):
    env = dict(os.environ)
    env["TZ"] = tz
    env.pop("TILLBOOK_CONFIG", None)
    env.pop("TILLBOOK_DATA_DIR", None)
    proc = subprocess.run(
        [sys.executable, "-m", "tillbook", "daily-totals", "--office", office,
         "--date", first, "--to", last, "--json"],
        cwd=TREE, env=env, capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    return [{k: day[k] for k in KEYS} for day in payload["days"]]


@pytest.mark.parametrize("tz", SERVER_TZS)
def test_mumbai_daily_totals_independent_of_server_timezone(tz):
    assert run_daily("BOM", "2026-03-13", "2026-03-15", tz) == EXPECTED[("BOM", "2026-03-13", "2026-03-15")]


@pytest.mark.parametrize("tz", SERVER_TZS)
def test_los_angeles_daily_totals_independent_of_server_timezone(tz):
    assert run_daily("LAX", "2026-03-13", "2026-03-14", tz) == EXPECTED[("LAX", "2026-03-13", "2026-03-14")]
