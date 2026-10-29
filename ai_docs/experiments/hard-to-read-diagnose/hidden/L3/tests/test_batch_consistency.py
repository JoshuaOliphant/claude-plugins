"""`stockflow batch` must report exactly what `stockflow import` reports.

The batch command is exercised many times in-process with a very small
thread switch interval so that worker threads interleave aggressively. The
inputs are small so each round is cheap; the expected result comes from the
sequential `import` command over the same files.
"""

import contextlib
import io
import json
import sys
from pathlib import Path

import pytest

from stockflow.cli import main

DATA = Path(__file__).resolve().parents[1] / "data" / "movements"


def run_cli(args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(args)
    assert code == 0, err.getvalue()
    return json.loads(out.getvalue())


@pytest.fixture
def small_inputs(tmp_path):
    for src in sorted(DATA.glob("*.csv")):
        lines = src.read_text(encoding="utf-8").splitlines()[:7]
        (tmp_path / src.name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def busy_switching():
    old = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        yield
    finally:
        sys.setswitchinterval(old)


def sequential(directory):
    files = [str(p) for p in sorted(directory.glob("*.csv"))]
    return run_cli(["import", *files, "--format", "json"])


def batch(directory, workers):
    return run_cli(["batch", str(directory), "--workers", str(workers), "-q", "--format", "json"])


def test_import_full_sample_totals():
    files = [str(p) for p in sorted(DATA.glob("*.csv"))]
    report = run_cli(["import", *files, "--format", "json"])
    assert report["totals"]["on_hand"] == 11085
    assert report["totals"]["movements"] == 1472
    assert report["ingest"] == {"rows_read": 1483, "posted": 1472, "rejected": 7, "duplicates": 4}


def test_batch_totals_match_import(small_inputs, busy_switching):
    expected = sequential(small_inputs)["totals"]
    mismatches = 0
    for _ in range(100):
        if batch(small_inputs, 8)["totals"] != expected:
            mismatches += 1
    assert mismatches == 0, f"{mismatches}/100 batch runs disagreed with import"


def test_batch_stock_levels_match_import(small_inputs, busy_switching):
    expected = sequential(small_inputs)["levels"]
    for round_no in range(100):
        got = batch(small_inputs, 4)["levels"]
        assert got == expected, f"stock levels differ from import on round {round_no}"


def test_batch_report_includes_every_posted_movement(small_inputs, busy_switching):
    for round_no in range(100):
        report = batch(small_inputs, 16)
        assert report["totals"]["movements"] == report["ingest"]["posted"], (
            f"round {round_no}: {report['ingest']['posted']} movements posted but "
            f"{report['totals']['movements']} in the report"
        )


def test_full_sample_batch_matches_import():
    files = [str(p) for p in sorted(DATA.glob("*.csv"))]
    expected = run_cli(["import", *files, "--format", "json"])
    for _ in range(3):
        got = batch(DATA, 8)
        assert got["totals"] == expected["totals"]
        assert got["ingest"] == expected["ingest"]
