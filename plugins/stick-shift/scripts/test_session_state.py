# ABOUTME: Tests for the stick-shift session_state.py manual session CLI.
# ABOUTME: Loads the script by path and re-points its .sdlc/ paths at a tmp dir.
"""Run: `python3 -m pytest plugins/stick-shift/scripts/test_session_state.py -v`
(or plain `python3 test_session_state.py` from this dir for the fallback runner)."""

import importlib.util
import json
import os
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "session_state", Path(__file__).with_name("session_state.py")
)
session_state = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(session_state)


def _point_at(tmp_path):
    session_state.SDLC_DIR = Path(".sdlc")
    session_state.STATE_FILE = session_state.SDLC_DIR / "state.json"
    session_state.PROGRESS_FILE = session_state.SDLC_DIR / "progress.md"
    session_state.DECISIONS_FILE = session_state.SDLC_DIR / "decisions.jsonl"


def _run(tmp_path, fn, **ns):
    """Chdir into tmp_path, re-point paths, call a cmd_* fn with a Namespace."""
    cwd = Path.cwd()
    os.chdir(tmp_path)
    _point_at(tmp_path)
    try:
        fn(session_state.argparse.Namespace(**ns))
    finally:
        os.chdir(cwd)


def _init(tmp_path, feature="cart-pricing", request="Build a cart engine"):
    _run(tmp_path, session_state.cmd_init, feature=feature, request=request)
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        return json.loads(session_state.STATE_FILE.read_text())
    finally:
        os.chdir(cwd)


def test_init_creates_session_in_INIT(tmp_path):
    state = _init(tmp_path)
    assert state["state"] == "INIT"
    assert state["feature"] == "cart-pricing"
    assert state["in_flight"] == []
    assert state["history"][0]["to"] == "INIT"


def test_init_is_idempotent(tmp_path):
    _init(tmp_path)
    # Second init must not clobber — it resumes.
    state = _init(tmp_path)
    assert state["state"] == "INIT"
    assert len(state["history"]) == 1


def _read_state(tmp_path):
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        return json.loads(session_state.STATE_FILE.read_text())
    finally:
        os.chdir(cwd)


def test_transition_records_history_and_state(tmp_path):
    _init(tmp_path)
    _run(tmp_path, session_state.cmd_transition, target="SPEC", reason="3 criteria")
    state = _read_state(tmp_path)
    assert state["state"] == "SPEC"
    assert state["history"][-1]["to"] == "SPEC"
    assert state["history"][-1]["reason"] == "3 criteria"


def test_off_graph_transition_nudges_but_proceeds(tmp_path, capsys):
    _init(tmp_path)  # state INIT
    # INIT normally → SPEC; jumping straight to BUILD must warn yet still record.
    _run(tmp_path, session_state.cmd_transition, target="BUILD", reason="skipping ahead")
    err = capsys.readouterr().err
    assert "NUDGE" in err
    assert _read_state(tmp_path)["state"] == "BUILD"


def test_unknown_state_is_rejected(tmp_path):
    import pytest

    _init(tmp_path)
    with pytest.raises(SystemExit):
        _run(tmp_path, session_state.cmd_transition, target="WAT", reason="x")


def test_decide_appends_jsonl(tmp_path):
    _init(tmp_path)
    _run(
        tmp_path,
        session_state.cmd_decide,
        decision="Decimal not float",
        why="exact rounding",
        irreversible=False,
    )
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        lines = session_state.DECISIONS_FILE.read_text().splitlines()
    finally:
        os.chdir(cwd)
    entry = json.loads(lines[0])
    assert entry["decision"] == "Decimal not float"
    assert entry["why"] == "exact rounding"
    assert entry["reversible"] is True


def test_task_in_flight_add_and_done(tmp_path):
    _init(tmp_path)
    _run(tmp_path, session_state.cmd_task, task_id="t1", done=False)
    _run(tmp_path, session_state.cmd_task, task_id="t2", done=False)
    _run(tmp_path, session_state.cmd_task, task_id="t1", done=True)
    assert _read_state(tmp_path)["in_flight"] == ["t2"]


def test_journal_renders_history_and_decisions(tmp_path, capsys):
    _init(tmp_path)
    _run(tmp_path, session_state.cmd_transition, target="SPEC", reason="3 criteria")
    _run(
        tmp_path,
        session_state.cmd_decide,
        decision="Decimal not float",
        why="exact rounding",
        irreversible=False,
    )
    _run(tmp_path, session_state.cmd_journal)
    out = capsys.readouterr().out
    assert "cart-pricing" in out
    assert "→ SPEC: 3 criteria" in out
    assert "Decimal not float" in out
