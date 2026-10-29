"""Grading tests: stock availability with backordered reservations.

Each test works on a private copy of the shipped database and drives the
application only through its public CLI (``python -m stockroom``).
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TREE = Path(__file__).resolve().parent.parent
SHIPPED_DB = TREE / "data" / "stockroom.db"


@pytest.fixture
def cli(tmp_path):
    db = tmp_path / "stockroom.db"
    shutil.copyfile(SHIPPED_DB, db)
    env = dict(os.environ)
    env["STOCKROOM_DB"] = str(db)
    env["STOCKROOM_TODAY"] = "2026-10-29"
    env.pop("STOCKROOM_SETTINGS", None)
    env.pop("STOCKROOM_WAREHOUSE", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    def run(*args, check=True):
        proc = subprocess.run(
            [sys.executable, "-m", "stockroom", *args],
            cwd=TREE, env=env, capture_output=True, text=True, timeout=30,
        )
        if check and proc.returncode != 0:
            raise AssertionError(f"stockroom {' '.join(args)} failed:\n{proc.stdout}\n{proc.stderr}")
        return proc

    return run


def availability(cli, sku, warehouse):
    out = cli("report", "availability", "--sku", sku, "--warehouse", warehouse, "--format", "json").stdout
    rows = json.loads(out)["rows"]
    assert len(rows) == 1, rows
    row = rows[0]
    return {k: row[k] for k in ("on_hand", "reserved", "available", "backordered")}


def test_baseline_backorder_is_reported(cli):
    assert availability(cli, "LMP-220", "MAIN") == {
        "on_hand": 0, "reserved": 10, "available": 0, "backordered": 10,
    }


def test_partial_receipts_keep_backorder_promised(cli):
    cli("receive", "LMP-220", "4", "--warehouse", "MAIN")
    assert availability(cli, "LMP-220", "MAIN") == {
        "on_hand": 4, "reserved": 10, "available": 0, "backordered": 6,
    }
    cli("receive", "LMP-220", "6", "--warehouse", "MAIN")
    assert availability(cli, "LMP-220", "MAIN") == {
        "on_hand": 10, "reserved": 10, "available": 0, "backordered": 0,
    }


def test_promised_stock_cannot_be_sold_to_non_backorder_customer(cli):
    cli("receive", "LMP-220", "4", "--warehouse", "MAIN")
    cli("receive", "LMP-220", "6", "--warehouse", "MAIN")
    proc = cli("order", "place", "--customer", "C002", "--warehouse", "MAIN", "--line", "LMP-220:2", check=False)
    assert proc.returncode != 0, proc.stdout
    assert availability(cli, "LMP-220", "MAIN")["reserved"] == 10


def test_partial_shipment_leaves_remaining_backorder(cli):
    cli("receive", "LMP-220", "4", "--warehouse", "MAIN")
    cli("order", "ship", "SO-1042")
    assert availability(cli, "LMP-220", "MAIN") == {
        "on_hand": 0, "reserved": 6, "available": 0, "backordered": 6,
    }
    # The other line on the order was fully covered and is unaffected.
    assert availability(cli, "CHR-310", "MAIN") == {
        "on_hand": 10, "reserved": 0, "available": 10, "backordered": 0,
    }
    cli("receive", "LMP-220", "6", "--warehouse", "MAIN")
    cli("order", "ship", "SO-1042")
    assert availability(cli, "LMP-220", "MAIN") == {
        "on_hand": 0, "reserved": 0, "available": 0, "backordered": 0,
    }


def test_cycle_count_does_not_release_reservations(cli):
    cli("count", "LMP-220", "3", "--warehouse", "MAIN")
    assert availability(cli, "LMP-220", "MAIN") == {
        "on_hand": 3, "reserved": 10, "available": 0, "backordered": 7,
    }


def test_transfer_into_backordered_warehouse(cli):
    cli("transfer", "LMP-220", "2", "--from", "EAST", "--to", "MAIN")
    assert availability(cli, "LMP-220", "MAIN") == {
        "on_hand": 2, "reserved": 10, "available": 0, "backordered": 8,
    }
    assert availability(cli, "LMP-220", "EAST") == {
        "on_hand": 1, "reserved": 0, "available": 1, "backordered": 0,
    }


def test_backorder_at_east_survives_receipt(cli):
    cli("receive", "MON-420", "2", "--warehouse", "EAST")
    assert availability(cli, "MON-420", "EAST") == {
        "on_hand": 3, "reserved": 4, "available": 0, "backordered": 1,
    }


def test_ordinary_stock_flow_unchanged(cli):
    cli("order", "place", "--customer", "C003", "--warehouse", "MAIN", "--line", "DSK-100:2")
    assert availability(cli, "DSK-100", "MAIN") == {
        "on_hand": 6, "reserved": 2, "available": 4, "backordered": 0,
    }
    cli("receive", "DSK-100", "3", "--warehouse", "MAIN")
    cli("order", "ship", "SO-1043")
    assert availability(cli, "DSK-100", "MAIN") == {
        "on_hand": 7, "reserved": 0, "available": 7, "backordered": 0,
    }


def test_open_orders_report_matches_reservations(cli):
    cli("receive", "LMP-220", "4", "--warehouse", "MAIN")
    cli("order", "ship", "SO-1042")
    out = cli("report", "open-orders", "--sku", "LMP-220", "--format", "json").stdout
    remaining = sum(r["remaining"] for r in json.loads(out)["rows"] if r["warehouse"] == "MAIN")
    assert remaining == availability(cli, "LMP-220", "MAIN")["reserved"] == 6
