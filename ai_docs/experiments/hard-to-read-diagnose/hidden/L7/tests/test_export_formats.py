import csv
import io
import json


def _read(path):
    return path.read_bytes().decode("utf-8")


def test_csv_extension_gives_plain_csv(run_cli, tmp_path):
    out = tmp_path / "report.csv"
    code, _ = run_cli("export", "data/sample.ledger", "-o", str(out))
    assert code == 0
    text = _read(out)
    assert not text.startswith("﻿")
    assert "\r\n" not in text
    lines = text.splitlines()
    assert lines[0] == "date,payee,account,category,amount,currency,memo"
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[1][:6] == ["2026-01-02", "Acme Corp Payroll", "checking", "income:salary", "4250.00", "USD"]
    amounts = [r[4] for r in rows[1:]]
    assert "-1018.66" in amounts
    assert len(rows) == 23


def test_explicit_csv_format_matches_extension(run_cli, tmp_path):
    a = tmp_path / "a.csv"
    b = tmp_path / "b.txt"
    assert run_cli("export", "data/sample.ledger", "-o", str(a))[0] == 0
    assert run_cli("export", "data/sample.ledger", "-f", "csv", "-o", str(b))[0] == 0
    assert _read(a) == _read(b)


def test_csv_roundtrip(run_cli, tmp_path):
    out = tmp_path / "april.csv"
    assert run_cli("export", "data/sample.csv", "-o", str(out))[0] == 0
    rows = list(csv.DictReader(io.StringIO(_read(out))))
    assert [r["amount"] for r in rows] == ["4250.00", "-1650.00", "-120.75", "-34.90", "-95.00"]
    assert rows[3]["payee"] == "Books, Maps & More"


def test_excel_eu_still_available_explicitly(run_cli, tmp_path):
    out = tmp_path / "eu.csv"
    code, _ = run_cli("export", "data/sample.ledger", "-f", "excel-eu", "-o", str(out))
    assert code == 0
    text = _read(out)
    assert text.startswith("﻿")
    first = text.lstrip("﻿").split("\r\n")[1]
    assert first.split(";")[:5] == ["02.01.2026", "Acme Corp Payroll", "checking", "income:salary", "4250,00"]


def test_other_extensions(run_cli, tmp_path):
    tsv = tmp_path / "r.tsv"
    js = tmp_path / "r.json"
    md = tmp_path / "r.md"
    for target in (tsv, js, md):
        assert run_cli("export", "data/sample.ledger", "-o", str(target))[0] == 0
    assert _read(tsv).splitlines()[0].split("\t")[0] == "date"
    assert json.loads(_read(js))["count"] == 22
    assert _read(md).startswith("# ")


def test_stdout_default_format_is_plain_csv(run_cli):
    code, text = run_cli("export", "data/sample.csv")
    assert code == 0
    assert text.splitlines()[1] == "2026-04-01,Acme Corp Payroll,checking,income:salary,4250.00,USD,April salary"


def test_formats_listing_csv_extension_owner(run_cli):
    code, text = run_cli("formats", "--json")
    assert code == 0
    formats = {f["name"]: f for f in json.loads(text)}
    assert {"csv", "excel-eu", "tsv", "json", "markdown", "html"} <= set(formats)
    assert ".csv" in formats["csv"]["extensions"]
