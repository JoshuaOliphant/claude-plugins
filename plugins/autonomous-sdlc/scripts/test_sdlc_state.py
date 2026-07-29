# ABOUTME: Tests for the sdlc_state.py state machine CLI.
# ABOUTME: Focuses on the per-project review-gate config written by `init`.
"""Run from this directory: `python3 -m pytest test_sdlc_state.py` (or plain
`python3 test_sdlc_state.py` for the bundled fallback runner)."""

import importlib.util
import json
import os
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "sdlc_state", Path(__file__).with_name("sdlc_state.py")
)
sdlc_state = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sdlc_state)


def _init(tmp_path, **overrides):
    """Run cmd_init in tmp_path with default args overridable by kwargs."""
    cwd = Path.cwd()
    os.chdir(tmp_path)
    # Re-point module-level paths at the temp dir.
    sdlc_state.SDLC_DIR = Path(".sdlc")
    sdlc_state.STATE_FILE = sdlc_state.SDLC_DIR / "state.json"
    sdlc_state.PROGRESS_FILE = sdlc_state.SDLC_DIR / "progress.md"
    sdlc_state.DECISIONS_FILE = sdlc_state.SDLC_DIR / "decisions.jsonl"
    try:
        args = sdlc_state.argparse.Namespace(
            feature=overrides.get("_feature", "demo"),
            request=overrides.get("_request", "do a thing"),
            max_iterations=50,
            max_attempts=3,
            max_wait_ticks=200,
            driver="goal",
            reviewers=overrides.get("reviewers", None),
            review_mode=overrides.get("review_mode", None),
        )
        sdlc_state.cmd_init(args)
        return json.loads(sdlc_state.STATE_FILE.read_text())
    finally:
        os.chdir(cwd)


def test_default_review_config_preserves_current_behavior(tmp_path):
    state = _init(tmp_path)
    assert "review" in state, "init must write a review config block"
    review = state["review"]
    # Default reviewers must be the built-in code-review skill (current behavior).
    assert review["reviewers"] == ["code-review"]
    # Default mode must block (findings become fix tasks → BUILD).
    assert review["mode"] == "block"


def test_custom_reviewers_are_recorded(tmp_path):
    state = _init(
        tmp_path,
        reviewers="code-review,security-review,pr-test-analyzer",
        review_mode="annotate",
    )
    review = state["review"]
    assert review["reviewers"] == [
        "code-review",
        "security-review",
        "pr-test-analyzer",
    ]
    assert review["mode"] == "annotate"


def test_invalid_review_mode_is_rejected(tmp_path):
    import pytest

    with pytest.raises(SystemExit):
        _init(tmp_path, review_mode="bogus")


def test_blank_reviewers_falls_back_to_default(tmp_path):
    # Empty/whitespace reviewers string must not produce an empty gate.
    state = _init(tmp_path, reviewers="  ")
    assert state["review"]["reviewers"] == ["code-review"]


def test_resume_backfills_missing_review_block(tmp_path):
    # A state.json written under v2.0.0 has no "review" key. Resuming through
    # init must backfill the default block and persist it, so the REVIEW gate
    # reader never KeyErrors.
    state = _init(tmp_path)  # establishes the temp dir + module paths
    legacy = dict(state)
    del legacy["review"]

    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        sdlc_state.STATE_FILE.write_text(json.dumps(legacy, indent=2) + "\n")
        args = sdlc_state.argparse.Namespace(
            feature="demo",
            request="do a thing",
            max_iterations=50,
            max_attempts=3,
            max_wait_ticks=200,
            driver="goal",
            reviewers=None,
            review_mode=None,
        )
        sdlc_state.cmd_init(args)
        persisted = json.loads(sdlc_state.STATE_FILE.read_text())
    finally:
        os.chdir(cwd)

    assert persisted["review"] == {"reviewers": ["code-review"], "mode": "block"}


def _repoint(tmp_path):
    sdlc_state.SDLC_DIR = Path(".sdlc")
    sdlc_state.STATE_FILE = sdlc_state.SDLC_DIR / "state.json"
    sdlc_state.PROGRESS_FILE = sdlc_state.SDLC_DIR / "progress.md"
    sdlc_state.DECISIONS_FILE = sdlc_state.SDLC_DIR / "decisions.jsonl"


def _run(tmp_path, fn, **ns):
    """Chdir into tmp_path, re-point paths, call a cmd_* fn with a Namespace."""
    cwd = Path.cwd()
    os.chdir(tmp_path)
    _repoint(tmp_path)
    try:
        fn(sdlc_state.argparse.Namespace(**ns))
    finally:
        os.chdir(cwd)


def _read_state(tmp_path):
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        return json.loads(sdlc_state.STATE_FILE.read_text())
    finally:
        os.chdir(cwd)


def _write_state(tmp_path, state):
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        sdlc_state.STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")
    finally:
        os.chdir(cwd)


# --- The "next increment" lifecycle (parity with stick-shift's increment) ---


def test_init_records_cycle_and_increments(tmp_path):
    state = _init(tmp_path)
    assert state["cycle"] == 1
    assert state["increments"] == []
    assert state["history"][0]["cycle"] == 1


def test_increment_starts_new_cycle_and_retargets(tmp_path):
    _init(tmp_path)  # feature=demo, cycle 1
    _run(
        tmp_path,
        sdlc_state.cmd_increment,
        feature="durability",
        request="persist to JSONL",
    )
    state = _read_state(tmp_path)
    assert state["cycle"] == 2
    assert state["feature"] == "durability"  # retargeted, no stale lie
    assert state["request"] == "persist to JSONL"
    assert state["state"] == "INIT"  # new increment begins at INIT
    assert state["in_flight"] == []
    assert "increment 2" in state["history"][-1]["reason"]
    assert state["history"][-1]["cycle"] == 2


def test_increment_archives_prior_increment(tmp_path):
    _init(tmp_path, _feature="cart", _request="build a cart")
    _run(tmp_path, sdlc_state.cmd_increment, feature="durability", request="x")
    archived = _read_state(tmp_path)["increments"]
    assert len(archived) == 1
    assert archived[0]["feature"] == "cart"
    assert archived[0]["request"] == "build a cart"
    assert archived[0]["cycle"] == 1


def test_increment_resets_loop_counters_but_keeps_config(tmp_path):
    _init(tmp_path, reviewers="security-review", review_mode="annotate")
    # Simulate a fully-run increment: burned iterations, wait ticks, attempts.
    s = _read_state(tmp_path)
    s["state"] = "DONE"
    s["iteration"] = 37
    s["wait_ticks"] = 12
    s["attempts"] = {"bd-1": 3}
    s["last_progress_iteration"] = 37
    _write_state(tmp_path, s)

    _run(tmp_path, sdlc_state.cmd_increment, feature="phase2", request="more")
    state = _read_state(tmp_path)
    # Per-run loop counters reset for a fresh increment.
    assert state["iteration"] == 0
    assert state["wait_ticks"] == 0
    assert state["attempts"] == {}
    assert state["last_progress_iteration"] == 0
    # Per-project config survives the increment untouched.
    assert state["budgets"]["max_iterations"] == 50
    assert state["review"] == {"reviewers": ["security-review"], "mode": "annotate"}
    assert state["driver"] == "goal"


def test_init_on_done_with_new_feature_auto_increments(tmp_path):
    # A plain re-run of `/sdlc "new thing"` after DONE must start increment 2,
    # not silently resume the DONE state and drop the new request.
    _init(tmp_path, _feature="cart", _request="build a cart")
    s = _read_state(tmp_path)
    s["state"] = "DONE"
    _write_state(tmp_path, s)

    _init(tmp_path, _feature="checkout", _request="add checkout")
    state = _read_state(tmp_path)
    assert state["cycle"] == 2
    assert state["state"] == "INIT"
    assert state["feature"] == "checkout"
    assert state["request"] == "add checkout"
    assert state["increments"][0]["feature"] == "cart"


def test_init_on_done_same_feature_just_resumes(tmp_path):
    # Re-running with the SAME feature on a DONE session is a no-op resume,
    # not a spurious empty increment.
    _init(tmp_path, _feature="cart", _request="build a cart")
    s = _read_state(tmp_path)
    s["state"] = "DONE"
    _write_state(tmp_path, s)

    _init(tmp_path, _feature="cart", _request="build a cart")
    state = _read_state(tmp_path)
    assert state["cycle"] == 1
    assert state["state"] == "DONE"
    assert state["increments"] == []


def test_init_on_in_progress_does_not_increment(tmp_path):
    # A new feature given while a loop is mid-flight (not DONE) must resume the
    # in-progress loop, never increment over live work.
    _init(tmp_path, _feature="cart", _request="build a cart")
    s = _read_state(tmp_path)
    s["state"] = "BUILD"
    _write_state(tmp_path, s)

    _init(tmp_path, _feature="something-else", _request="other")
    state = _read_state(tmp_path)
    assert state["cycle"] == 1
    assert state["state"] == "BUILD"
    assert state["feature"] == "cart"  # live work untouched


def test_resume_preserves_existing_review_block(tmp_path):
    # An already-current state.json must not be rewritten on resume — the
    # custom review config survives untouched (idempotency).
    state = _init(
        tmp_path, reviewers="security-review", review_mode="annotate"
    )

    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        before = sdlc_state.STATE_FILE.read_text()
        args = sdlc_state.argparse.Namespace(
            feature="demo",
            request="do a thing",
            max_iterations=50,
            max_attempts=3,
            max_wait_ticks=200,
            driver="goal",
            reviewers=None,
            review_mode=None,
        )
        sdlc_state.cmd_init(args)
        after = sdlc_state.STATE_FILE.read_text()
    finally:
        os.chdir(cwd)

    assert state["review"] == {"reviewers": ["security-review"], "mode": "annotate"}
    # Byte-identical: resume of a current file must not touch disk.
    assert after == before


# --- Run capture + scoring (the /sdlc-retro ledger) -------------------------


def _terminal_via_transition(tmp_path, target, reason):
    """Drive the state to `target` through cmd_transition (legal edge required)."""
    _run(tmp_path, sdlc_state.cmd_transition, target=target, reason=reason)


def test_score_reflects_outcome_and_rework(tmp_path):
    _init(tmp_path)
    s = _read_state(tmp_path)
    s["state"] = "DONE"
    s["iteration"] = 12
    s["attempts"] = {"bd-1": 1, "bd-2": 2, "bd-3": 4, "bd-4": 1}  # bd-3 exceeded
    s["history"] = [
        {"at": "t", "to": st, "reason": "r"}
        for st in [
            "INIT", "SPEC", "PLAN", "BUILD", "VERIFY", "BUILD",  # verify bounce
            "VERIFY", "REVIEW", "BUILD", "VERIFY", "REVIEW",     # review roundtrip
            "SHIP", "DONE",
        ]
    ]
    _write_state(tmp_path, s)
    metrics = sdlc_state.compute_score(_read_state(tmp_path))
    assert metrics["outcome"] == "DONE"
    assert metrics["rework"] == {
        "verify_bounces": 1,
        "review_roundtrips": 1,
        "replans": 0,
        "repairs": 0,
    }
    assert metrics["tasks_attempted"] == 4
    assert metrics["attempts_exceeded"] == 1
    # 12 iterations / 4 tasks = 3.0/task → full efficiency; 2/12 backward edges.
    assert 0.0 < metrics["score"] <= 1.0
    blocked = dict(s, state="BLOCKED")
    assert sdlc_state.compute_score(blocked)["score"] < metrics["score"], (
        "outcome must dominate: same trace but BLOCKED scores lower"
    )


def test_terminal_transition_archives_run(tmp_path):
    archive_root = tmp_path / "archive-root"
    os.environ["SDLC_RUNS_DIR"] = str(archive_root)
    try:
        _init(tmp_path, _feature="cart")
        s = _read_state(tmp_path)
        s["state"] = "SHIP"
        _write_state(tmp_path, s)
        (tmp_path / ".sdlc" / "signs.md").write_text("# Signs\n- Sign: check first\n")
        _terminal_via_transition(tmp_path, "DONE", "https://example.com/pr/1")

        ledger = (archive_root / "runs.jsonl").read_text().splitlines()
        assert len(ledger) == 1
        record = json.loads(ledger[0])
        assert record["feature"] == "cart"
        assert record["outcome"] == "DONE"
        assert record["terminal_reason"] == "https://example.com/pr/1"
        assert record["signs_active"] == 1  # header line not counted
        assert record["plugin_version"] not in ("", None)
        run_dir = Path(record["archive"])
        assert (run_dir / "state.json").exists()
        assert (run_dir / "signs.md").exists()
        # The archived state is the terminal one, not a stale pre-save copy.
        assert json.loads((run_dir / "state.json").read_text())["state"] == "DONE"
    finally:
        del os.environ["SDLC_RUNS_DIR"]


def test_forced_block_archives_run(tmp_path):
    # Budget force-blocks go through block(), not cmd_transition — the most
    # informative runs (failures) must be captured too.
    archive_root = tmp_path / "archive-root"
    os.environ["SDLC_RUNS_DIR"] = str(archive_root)
    try:
        _init(tmp_path)
        s = _read_state(tmp_path)
        s["state"] = "BUILD"
        s["iteration"] = 50  # at the budget; next tick exceeds it
        s["last_progress_iteration"] = 50
        _write_state(tmp_path, s)
        import pytest

        with pytest.raises(SystemExit):
            _run(tmp_path, sdlc_state.cmd_tick, waiting=False)
        record = json.loads((archive_root / "runs.jsonl").read_text().splitlines()[0])
        assert record["outcome"] == "BLOCKED"
        assert "max_iterations" in record["terminal_reason"]
        assert record["score"] < 0.5  # BLOCKED forfeits the outcome half
    finally:
        del os.environ["SDLC_RUNS_DIR"]


def test_archive_failure_never_breaks_the_transition(tmp_path):
    # Point the archive root at a *file* so mkdir fails: the transition must
    # still land (archive is best-effort by design).
    poison = tmp_path / "not-a-dir"
    poison.write_text("occupied")
    os.environ["SDLC_RUNS_DIR"] = str(poison)
    try:
        _init(tmp_path)
        s = _read_state(tmp_path)
        s["state"] = "SHIP"
        _write_state(tmp_path, s)
        _terminal_via_transition(tmp_path, "DONE", "pr")
        assert _read_state(tmp_path)["state"] == "DONE"
    finally:
        del os.environ["SDLC_RUNS_DIR"]


def test_score_only_sees_current_increment(tmp_path):
    # A messy increment 1 must not drag down increment 2's score: the trace
    # window starts at the latest INIT entry.
    _init(tmp_path)
    s = _read_state(tmp_path)
    s["history"] = [
        {"at": "t", "to": st, "reason": "r"}
        for st in ["INIT", "SPEC", "PLAN", "BUILD", "VERIFY", "BUILD", "VERIFY",
                   "REVIEW", "BUILD", "VERIFY", "REVIEW", "SHIP", "DONE"]
    ]
    _write_state(tmp_path, s)
    _run(tmp_path, sdlc_state.cmd_increment, feature="phase2", request="more")
    s = _read_state(tmp_path)
    s["state"] = "DONE"
    _write_state(tmp_path, s)
    metrics = sdlc_state.compute_score(_read_state(tmp_path))
    assert metrics["rework"] == {
        "verify_bounces": 0,
        "review_roundtrips": 0,
        "replans": 0,
        "repairs": 0,
    }


if __name__ == "__main__":
    # Minimal fallback runner so the suite works without pytest installed.
    import tempfile
    import traceback

    tests = [
        test_default_review_config_preserves_current_behavior,
        test_custom_reviewers_are_recorded,
        test_blank_reviewers_falls_back_to_default,
        test_resume_backfills_missing_review_block,
        test_resume_preserves_existing_review_block,
        test_init_records_cycle_and_increments,
        test_increment_starts_new_cycle_and_retargets,
        test_increment_archives_prior_increment,
        test_increment_resets_loop_counters_but_keeps_config,
        test_init_on_done_with_new_feature_auto_increments,
        test_init_on_done_same_feature_just_resumes,
        test_init_on_in_progress_does_not_increment,
        test_score_reflects_outcome_and_rework,
        test_terminal_transition_archives_run,
        test_archive_failure_never_breaks_the_transition,
        test_score_only_sees_current_increment,
    ]
    # The pytest.raises tests need pytest; skip them in fallback mode.
    failures = 0
    for t in tests:
        with tempfile.TemporaryDirectory() as d:
            try:
                t(Path(d))
                print(f"PASS {t.__name__}")
            except Exception:
                failures += 1
                print(f"FAIL {t.__name__}")
                traceback.print_exc()
    raise SystemExit(1 if failures else 0)
