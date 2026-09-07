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
    sdlc_state.LOOP_MD_FILE = Path(".claude") / "loop.md"
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


# --- native /loop driver: init writes .claude/loop.md, set-driver accepts loop ---


def test_init_writes_loop_md_with_feature_and_state_cli_path(tmp_path):
    _init(tmp_path, _feature="user-auth")
    loop_md = tmp_path / ".claude" / "loop.md"
    assert loop_md.exists()
    body = loop_md.read_text()
    assert "user-auth" in body
    # The absolute CLI path is baked in so the prompt needs no env expansion.
    assert str(Path(sdlc_state.__file__).resolve()) in body
    assert "${CLAUDE_PLUGIN_ROOT}" not in body
    assert "ScheduleWakeup" in body


def test_init_never_overwrites_a_user_owned_loop_md(tmp_path):
    # No marker line → the user's own prompt; init leaves it alone.
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "loop.md").write_text("mine\n")
    _init(tmp_path)
    assert (tmp_path / ".claude" / "loop.md").read_text() == "mine\n"


def _stale_loop_md(tmp_path, feature="old-feature"):
    loop_md = tmp_path / ".claude" / "loop.md"
    loop_md.parent.mkdir(exist_ok=True)
    loop_md.write_text(
        f"{sdlc_state.LOOP_MD_MARKER} (stale)\n\n"
        f"loop for **{feature}**: python3 /old/plugin/path/sdlc_state.py tick\n"
    )
    return loop_md


def test_resume_regenerates_our_stale_loop_md(tmp_path):
    # The baked absolute CLI path goes stale when the plugin is upgraded or the
    # checkout moves; resume must rewrite our file with the current path.
    _init(tmp_path, _feature="cart")
    loop_md = _stale_loop_md(tmp_path, feature="cart")
    s = _read_state(tmp_path)
    s["state"] = "BUILD"
    _write_state(tmp_path, s)

    _init(tmp_path, _feature="cart")
    body = loop_md.read_text()
    assert "/old/plugin/path" not in body
    assert str(Path(sdlc_state.__file__).resolve()) in body


def test_increment_retargets_loop_md_feature(tmp_path):
    _init(tmp_path, _feature="cart", _request="build a cart")
    s = _read_state(tmp_path)
    s["state"] = "DONE"
    _write_state(tmp_path, s)
    _stale_loop_md(tmp_path, feature="cart")

    _init(tmp_path, _feature="checkout", _request="add checkout")
    body = (tmp_path / ".claude" / "loop.md").read_text()
    assert "**checkout**" in body
    assert "**cart**" not in body


def _transition(tmp_path, target, from_state=None):
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        if from_state:
            s = json.loads(sdlc_state.STATE_FILE.read_text())
            s["state"] = from_state
            sdlc_state.STATE_FILE.write_text(json.dumps(s))
        sdlc_state.cmd_transition(
            sdlc_state.argparse.Namespace(target=target, reason="test")
        )
    finally:
        os.chdir(cwd)


def test_transition_done_removes_our_loop_md(tmp_path):
    # Otherwise the SHIP report's "run a bare /loop to babysit the PR" would
    # re-enter the finished ritual instead of the built-in PR prompt.
    _init(tmp_path)
    loop_md = tmp_path / ".claude" / "loop.md"
    assert loop_md.exists()
    _transition(tmp_path, "DONE", from_state="SHIP")
    assert not loop_md.exists()
    assert "removed" in (tmp_path / ".sdlc" / "progress.md").read_text()


def test_transition_done_keeps_user_owned_loop_md(tmp_path):
    (tmp_path / ".claude").mkdir()
    loop_md = tmp_path / ".claude" / "loop.md"
    loop_md.write_text("mine\n")
    _init(tmp_path)
    _transition(tmp_path, "DONE", from_state="SHIP")
    assert loop_md.read_text() == "mine\n"


def test_transition_blocked_removes_loop_md_and_resume_rewrites_it(tmp_path):
    _init(tmp_path, _feature="cart")
    loop_md = tmp_path / ".claude" / "loop.md"
    _transition(tmp_path, "BLOCKED", from_state="BUILD")
    assert not loop_md.exists()
    # The human fixes the blocker and re-runs /sdlc: the prompt comes back.
    _init(tmp_path, _feature="cart")
    assert loop_md.exists()
    assert "**cart**" in loop_md.read_text()


def test_forced_block_from_tick_removes_loop_md(tmp_path):
    _init(tmp_path)
    loop_md = tmp_path / ".claude" / "loop.md"
    s = _read_state(tmp_path)
    s["state"] = "BUILD"
    s["iteration"] = s["budgets"]["max_iterations"]
    _write_state(tmp_path, s)
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        try:
            sdlc_state.cmd_tick(sdlc_state.argparse.Namespace(waiting=False))
        except SystemExit as e:
            assert e.code == 1
        else:
            raise AssertionError("tick past the budget should exit 1")
    finally:
        os.chdir(cwd)
    assert _read_state(tmp_path)["state"] == "BLOCKED"
    assert not loop_md.exists()


def test_set_driver_accepts_loop(tmp_path):
    _init(tmp_path)
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        sdlc_state.cmd_set_driver(sdlc_state.argparse.Namespace(driver="loop"))
        assert json.loads(sdlc_state.STATE_FILE.read_text())["driver"] == "loop"
    finally:
        os.chdir(cwd)
    assert "loop" in sdlc_state.DRIVERS


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
        test_init_writes_loop_md_with_feature_and_state_cli_path,
        test_init_never_overwrites_a_user_owned_loop_md,
        test_resume_regenerates_our_stale_loop_md,
        test_increment_retargets_loop_md_feature,
        test_transition_done_removes_our_loop_md,
        test_transition_done_keeps_user_owned_loop_md,
        test_transition_blocked_removes_loop_md_and_resume_rewrites_it,
        test_forced_block_from_tick_removes_loop_md,
        test_set_driver_accepts_loop,
    ]
    # The pytest.raises test needs pytest; skip it in fallback mode.
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
