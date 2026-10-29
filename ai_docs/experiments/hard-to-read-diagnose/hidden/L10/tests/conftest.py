import json
import sys
from pathlib import Path

import pytest

TREE = Path(__file__).resolve().parent.parent
if str(TREE) not in sys.path:
    sys.path.insert(0, str(TREE))

ACME_IDS = sorted(
    item["id"]
    for page in sorted((TREE / "feeds" / "acme").glob("p*.json"))
    for item in json.loads(page.read_text())["items"]
    if item["posted"] >= "2026-09-01"
)
NOVA_IDS = sorted(
    item["id"]
    for page in sorted((TREE / "feeds" / "nova").glob("p*.json"))
    for item in json.loads(page.read_text())["items"]
)


def write_config(tmp_path, sources, *, validate=False, attempts=3):
    lines = [
        "[ledger]",
        'base_currency = "USD"',
        f'output = "{(tmp_path / "ledger.jsonl").as_posix()}"',
        "[feeds]",
        f'root = "{(TREE / "feeds").as_posix()}"',
        "[retry]",
        f"attempts = {attempts}",
        "backoff_seconds = 0",
        "[validation]",
        f"enabled = {'true' if validate else 'false'}",
        "sample_size = 25",
    ]
    for src in sources:
        lines.append("[[sources]]")
        for key, value in src.items():
            if isinstance(value, Path):
                value = value.as_posix()
            lines.append(f'{key} = "{value}"')
    path = tmp_path / "run.toml"
    path.write_text("\n".join(lines) + "\n")
    return path


ACME = {"name": "acme-feed", "kind": "feed", "feed": "acme", "since": "2026-09-01"}
NOVA = {"name": "nova-feed", "kind": "feed", "feed": "nova"}
BANK = {"name": "bank", "kind": "csv", "path": TREE / "samples" / "bank.csv", "date_format": "%d/%m/%Y"}
CARD = {"name": "card", "kind": "jsonl", "path": TREE / "samples" / "card.jsonl"}


def ledger_ids(tmp_path, source=None):
    ids = []
    with open(tmp_path / "ledger.jsonl") as fh:
        for line in fh:
            doc = json.loads(line)
            if source is None or doc["source"] == source:
                ids.append(doc["id"])
    return sorted(ids)


@pytest.fixture
def no_sleep():
    calls = []
    return calls.append
