import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

TREE = Path(__file__).resolve().parent.parent
AS_OF = "2026-10-28T12:00:00Z"


def _ignore(directory, names):
    skip = {"tests", "__pycache__", "var", ".pytest_cache"}
    return [n for n in names if n in skip]


@pytest.fixture
def project(tmp_path):
    dest = tmp_path / "proj"
    shutil.copytree(TREE, dest, ignore=_ignore)
    return dest


def _env(extra=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("RELAYDESK_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(extra or {})
    return env


def run(project, *args, extra_env=None):
    proc = subprocess.run(
        [sys.executable, "-m", "relaydesk", *args],
        cwd=project, env=_env(extra_env), capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def dry_run_batches(project, *extra, extra_env=None):
    out = run(project, "send", "--dry-run", "--json", "--as-of", AS_OF, *extra,
              extra_env=extra_env)
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def configured_batch_size(project):
    with (project / "config" / "relaydesk.toml").open("rb") as fh:
        return tomllib.load(fh)["delivery"]["batch_size"]


def set_batch_size(project, value):
    path = project / "config" / "relaydesk.toml"
    text = path.read_text()
    new, n = re.subn(r"(?m)^batch_size\s*=\s*\d+", f"batch_size = {value}", text)
    assert n == 1
    path.write_text(new)


def assert_chunked(batches, size):
    sizes = [b["size"] for b in batches]
    assert max(sizes) == size, sizes
    by_channel = {}
    for b in batches:
        by_channel.setdefault(b["channel"], []).append(b["size"])
    for channel, chunks in by_channel.items():
        assert all(c == size for c in chunks[:-1]), (channel, chunks)
        assert 0 < chunks[-1] <= size, (channel, chunks)


def test_dry_run_uses_batch_size_from_config_file(project):
    size = configured_batch_size(project)
    assert size == 50
    assert_chunked(dry_run_batches(project), size)


def test_editing_config_file_batch_size_takes_effect(project):
    set_batch_size(project, 7)
    assert_chunked(dry_run_batches(project), 7)


def test_config_command_reports_file_value(project):
    data = json.loads(run(project, "config", "--json"))
    assert data["delivery.batch_size"] == configured_batch_size(project)
    assert data["delivery.endpoint"] == "https://hooks.example.invalid/helpdesk/v2"
    assert data["delivery.transport"] == "outbox"


def test_real_send_writes_outbox_batches_of_configured_size(project):
    run(project, "send", "--as-of", AS_OF)
    files = sorted((project / "var" / "outbox").glob("*.json"))
    counts = [json.loads(f.read_text())["count"] for f in files]
    assert max(counts) == configured_batch_size(project), counts


def test_environment_variable_still_overrides_file(project):
    assert_chunked(dry_run_batches(project, extra_env={"RELAYDESK_BATCH": "9"}), 9)


def test_command_line_flag_overrides_everything(project):
    batches = dry_run_batches(project, "--batch-size", "5",
                              extra_env={"RELAYDESK_BATCH": "9"})
    assert_chunked(batches, 5)


def test_every_routed_ticket_appears_once(project):
    batches = dry_run_batches(project)
    ids = [t for b in batches for t in b["tickets"]]
    assert len(ids) == len(set(ids)) == 139
    assert {b["channel"] for b in batches} == {"billing", "incidents", "support"}
    for b in batches:
        assert b["endpoint"] == "https://hooks.example.invalid/helpdesk/v2/" + b["channel"]
