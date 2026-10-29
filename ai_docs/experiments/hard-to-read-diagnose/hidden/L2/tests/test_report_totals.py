import csv
import decimal
import json
import random
import re
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

TREE = Path(__file__).resolve().parents[1]
DATA = TREE / "data"


def run(*args):
    proc = subprocess.run(
        [sys.executable, "-m", "ledgerly", *map(str, args)],
        cwd=TREE,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(TREE), "PYTHONHASHSEED": "0"},
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def amount(label, text):
    match = re.search(rf"^{re.escape(label)}:\s*([\d,]+\.\d\d) USD", text, re.M)
    assert match, f"{label!r} not found in output:\n{text}"
    return Decimal(match.group(1).replace(",", ""))


def exact_sum(values):
    with decimal.localcontext(decimal.Context(prec=60)):
        return sum(values, Decimal(0))


@pytest.fixture
def big_export(tmp_path):
    """USD-only, tax-free export whose total is well over a million."""
    customers = {"customers": [
        {"id": "K1", "name": "Alpha Industrial", "region": "US-OR"},
        {"id": "K2", "name": "Beta Freight", "region": "US-OR"},
        {"id": "K3", "name": "Gamma Labs", "region": "EXEMPT"},
    ]}
    (tmp_path / "customers.json").write_text(json.dumps(customers))
    (tmp_path / "fx.json").write_text(json.dumps({"base": "USD", "rates": {}}))
    rng = random.Random(4242)
    rows, totals = [], {}
    for n in range(1, 41):
        inv = f"T-{n:03d}"
        cust = ("K1", "K2", "K3")[n % 3]
        month = (n - 1) % 4 + 1
        lines = [("SVC", "Service", "1", f"{rng.randint(60000, 99000)}.{rng.randint(0, 99):02d}"),
                 ("FEE", "Handling", "3", f"{rng.randint(1, 90)}.{rng.randint(0, 99):02d}")]
        for sku, desc, qty, price in lines:
            rows.append([inv, cust, f"2025-{month:02d}-{n % 27 + 1:02d}", "USD", sku, desc, qty, price])
        totals[inv] = exact_sum(Decimal(q) * Decimal(p) for _, _, q, p in lines)
    with (tmp_path / "big.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["invoice_id", "customer_id", "issue_date", "currency",
                         "sku", "description", "quantity", "unit_price"])
        writer.writerows(rows)
    return tmp_path, totals


def common(tmp):
    return ["--customers", tmp / "customers.json", "--fx-rates", tmp / "fx.json"]


def test_full_year_report_grand_total_matches_invoice_total():
    src = DATA / "invoices_2025.csv"
    expected = amount("Grand total", run("invoice", "total", src))
    report = run("report", "summary", src, "--as-of", "2026-01-15",
                 "--payments", DATA / "payments_2025.json")
    assert amount("Grand total", report) == expected


def test_report_grand_total_is_exact_for_large_export(big_export):
    tmp, totals = big_export
    expected = exact_sum(totals.values())
    assert expected > 1_000_000
    report = run("report", "summary", tmp / "big.csv", "--as-of", "2025-12-31", *common(tmp))
    assert amount("Grand total", report) == expected
    assert amount("Grand total", run("invoice", "total", tmp / "big.csv", *common(tmp))) == expected


def test_report_collected_and_outstanding_are_exact(big_export):
    tmp, totals = big_export
    unpaid = {"T-001", "T-017"}
    payments = [
        {"id": f"P{i}", "invoice": inv, "received": "2025-06-01", "amount": f"{amt:.2f}"}
        for i, (inv, amt) in enumerate(sorted(totals.items())) if inv not in unpaid
    ]
    (tmp / "payments.json").write_text(json.dumps({"payments": payments}))
    report = run("report", "summary", tmp / "big.csv", "--as-of", "2025-12-31",
                 "--payments", tmp / "payments.json", *common(tmp))
    collected = exact_sum(v for k, v in totals.items() if k not in unpaid)
    outstanding = exact_sum(totals[k] for k in unpaid)
    assert collected > 1_000_000
    assert amount("Collected", report) == collected
    assert amount("Outstanding", report) == outstanding


def test_aging_total_outstanding_is_exact(big_export):
    tmp, totals = big_export
    (tmp / "payments.json").write_text(json.dumps({"payments": []}))
    out = run("report", "aging", tmp / "big.csv", "--as-of", "2025-12-31",
              "--payments", tmp / "payments.json", *common(tmp))
    assert amount("Total outstanding", out) == exact_sum(totals.values())


def test_small_export_totals_agree():
    src = DATA / "invoices_2025_q3_sample.csv"
    expected = amount("Grand total", run("invoice", "total", src))
    report = run("report", "summary", src, "--as-of", "2025-10-31")
    assert amount("Grand total", report) == expected


def test_monthly_growth_column(tmp_path):
    (tmp_path / "customers.json").write_text(json.dumps(
        [{"id": "K1", "name": "Alpha Industrial", "region": "US-OR"}]))
    (tmp_path / "fx.json").write_text(json.dumps({"base": "USD", "rates": {}}))
    (tmp_path / "small.csv").write_text(
        "invoice_id,customer_id,issue_date,currency,sku,description,quantity,unit_price\n"
        "A1,K1,2025-01-10,USD,SVC,Service,1,1000.00\n"
        "A2,K1,2025-02-10,USD,SVC,Service,1,1500.00\n"
        "A3,K1,2025-03-10,USD,SVC,Service,1,1200.00\n"
    )
    out = run("report", "summary", tmp_path / "small.csv", "--as-of", "2025-04-01",
              "--only", "trend", *common(tmp_path))
    assert re.search(r"^2025-02\s+1,500\.00 USD\s+\+50\.0%$", out, re.M), out
    assert re.search(r"^2025-03\s+1,200\.00 USD\s+-20\.0%$", out, re.M), out
    assert re.search(r"^Avg monthly growth:\s+\+9\.5%$", out, re.M), out
