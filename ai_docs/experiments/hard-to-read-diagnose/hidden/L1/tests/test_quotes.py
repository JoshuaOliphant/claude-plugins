"""Grading tests: quotes must reflect the current rate cards for every input."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "samples" / "manifest-2026-10.csv"
SHIP_DATE = "2026-10-05"


def run_cli(args, cache_dir=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("FREIGHTDESK_")}
    if cache_dir is not None:
        env["FREIGHTDESK_CACHE_DIR"] = str(cache_dir)
    proc = subprocess.run(
        [sys.executable, "-m", "freightdesk", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def quote_json(args, cache_dir=None):
    return json.loads(run_cli(["quote", *args, "--ship-date", SHIP_DATE, "--format", "json"], cache_dir))


def test_reported_parcel_uses_current_nordline_rate_card():
    # 45x35x18 cm = 28350 cm3 / 5000 = 5.67 kg -> 6 kg billable, zone 3 band <=10 kg: 11.20 + 8.5% fuel.
    q = quote_json(["--carrier", "NORDLINE", "--to", "DE-80331", "--parcel", "45x35x18@2"])
    assert q["parcels"][0]["dim_weight_kg"] == "5.67"
    assert q["parcels"][0]["billable_kg"] == "6"
    assert q["total"] == {"amount": "12.15", "currency": "EUR"}


def test_same_parcel_with_different_spelling_agrees():
    a = quote_json(["--carrier", "NORDLINE", "--to", "DE-80331", "--parcel", "45x35x18@2"])
    b = quote_json(["--carrier", "NORDLINE", "--to", "DE-80331", "--dims", "45 x 35 x 18", "--weight", "2.00"])
    assert a == b


@pytest.mark.parametrize(
    "args",
    [
        ["--carrier", "NORDLINE", "--to", "DE-70173", "--parcel", "50x40x30@4.0"],
        ["--carrier", "NORDLINE", "--to", "DE-90402", "--parcel", "38x28x24@1.9", "--residential"],
        ["--carrier", "NORDLINE", "--to", "NL-1012AB", "--parcel", "55x45x35@6.0", "--parcel", "30x30x30@2.2"],
        ["--carrier", "NORDLINE", "--to", "AT-1010", "--parcel", "40x30x30@2.5"],
        ["--carrier", "ALPENPOST", "--to", "AT-1010", "--parcel", "45x35x18@2.0"],
        ["--carrier", "SWIFTPAK", "--to", "DE-80331", "--parcel", "45x35x18@2.0", "--residential"],
        ["--carrier", "NORDLINE", "--to", "DE-80331", "--parcel", "45x35x18@2", "--currency", "CHF"],
    ],
)
def test_single_quotes_match_a_cold_cache(args, tmp_path):
    shipped = quote_json(args)
    cold = quote_json(args, cache_dir=tmp_path / "cold")
    assert shipped == cold


@pytest.mark.parametrize("fmt", ["json", "csv"])
def test_manifest_matches_a_cold_cache(fmt, tmp_path):
    args = ["batch", str(MANIFEST), "--ship-date", SHIP_DATE, "--format", fmt]
    shipped = run_cli(args)
    cold = run_cli(args, cache_dir=tmp_path / "cold")
    assert shipped == cold


def test_manifest_billable_weights_follow_rate_card(tmp_path):
    out = json.loads(run_cli(["batch", str(MANIFEST), "--ship-date", SHIP_DATE, "--format", "json"]))
    tariffs = {}
    for quote in out:
        carrier = quote["carrier"]
        if carrier not in tariffs:
            tariffs[carrier] = json.loads((ROOT / "data" / "tariffs" / f"{carrier.lower()}.json").read_text())
    rows = {}
    import csv
    from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

    with MANIFEST.open(newline="") as fh:
        for row in csv.DictReader(fh):
            rows.setdefault(row["reference"], []).append(row)
    for quote in out:
        tariff = tariffs[quote["carrier"]]
        divisor = Decimal(str(tariff["dim_divisor"]))
        step = Decimal(tariff["weight_step_kg"])
        for parcel, row in zip(quote["parcels"], rows[quote["reference"]]):
            l, w, h = (Decimal(x) for x in row["dims"].split("x"))
            dim = (l * w * h / divisor).quantize(Decimal("0.01"), ROUND_HALF_UP)
            billable = max(Decimal(row["weight_kg"]), dim)
            billable = (billable / step).to_integral_value(ROUND_CEILING) * step
            assert Decimal(parcel["dim_weight_kg"]) == dim, (quote["reference"], parcel)
            assert Decimal(parcel["billable_kg"]) == billable, (quote["reference"], parcel)
