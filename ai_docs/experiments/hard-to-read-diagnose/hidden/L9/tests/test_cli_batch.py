"""The batch CLI must give each request the summary it would get on its own."""

import json
import os
import subprocess
import sys
from pathlib import Path

TREE = Path(__file__).resolve().parent.parent
SAMPLES = TREE / "samples" / "requests.jsonl"


def _env():
    env = dict(os.environ, PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1")
    env.pop("BASKETRY_SETTINGS", None)
    env.pop("BASKETRY_DATA_DIR", None)
    return env


def _run_cli(args, stdin=None):
    proc = subprocess.run(
        [sys.executable, "-m", "basketry", *args], input=stdin, capture_output=True,
        text=True, cwd=TREE, env=_env(), timeout=30, check=True,
    )
    return proc.stdout


def _requests():
    lines = SAMPLES.read_text(encoding="utf-8").splitlines()
    return [line for line in lines if line.strip() and not line.lstrip().startswith("#")]


def test_batch_summaries_match_individual_runs():
    batch = [json.loads(line) for line in _run_cli(["summarize", "--format", "json", str(SAMPLES)]).splitlines()]
    requests = _requests()
    assert len(batch) == len(requests)
    for request, from_batch in zip(requests, batch):
        alone = json.loads(_run_cli(["summarize", "--format", "json", "-"], stdin=request + "\n"))
        assert from_batch == alone, from_batch["order_id"]


def test_batch_text_receipt_for_second_customer():
    out = _run_cli(["summarize", "--customer", "C-1002", str(SAMPLES)])
    receipt = out.split("Order W-1002", 1)[1].split("Order W-1005", 1)[0]
    assert "Grace Hopper" in receipt
    assert "Merino" not in receipt
    assert "Happy birthday" not in receipt
