# ABOUTME: Tests for loop-stop-hook.sh — the autonomous-sdlc Stop-hook loop driver.
# ABOUTME: Locks the wait-aware behavior: a stop is allowed while builders are in flight.
"""Run from anywhere: `uv run --with pytest python -m pytest test_loop_stop_hook.py`
(or plain `python3 test_loop_stop_hook.py` for the bundled fallback runner).

The hook's contract: given a `.sdlc/state.json` in the current directory, it
prints a Stop-hook decision on stdout. `{"decision": "block", ...}` re-prompts the
agent (another loop iteration); anything else (an empty `{}` or no output) lets the
session stop. These tests drive the real shipped script, not a reimplementation.
"""

import json
import subprocess
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "scripts" / "loop-stop-hook.sh"

# The substring that marks a re-prompt (a blocked stop). Allow paths emit `{}` or
# nothing, so its absence means "the loop was allowed to rest / release".
BLOCK_MARKER = '"decision": "block"'


def run_hook(tmp_path, state=None, hook_blocks=None):
    """Run the Stop hook in tmp_path with an optional .sdlc/state.json.

    Returns (stdout, returncode). When state is None, no state.json is written
    (simulating a directory with no active loop).
    """
    sdlc = tmp_path / ".sdlc"
    if state is not None or hook_blocks is not None:
        sdlc.mkdir(exist_ok=True)
    if state is not None:
        (sdlc / "state.json").write_text(json.dumps(state))
    if hook_blocks is not None:
        (sdlc / ".hook-blocks").write_text(str(hook_blocks))
    result = subprocess.run(
        ["bash", str(HOOK)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    return result.stdout, result.returncode


def _build_state(**overrides):
    """A minimal active-loop state, BUILD with nothing in flight by default."""
    state = {"state": "BUILD", "driver": "auto", "in_flight": []}
    state.update(overrides)
    return state


def test_no_state_file_is_noop(tmp_path):
    out, code = run_hook(tmp_path, state=None)
    assert code == 0
    assert BLOCK_MARKER not in out


def test_build_without_inflight_blocks(tmp_path):
    # A non-terminal state with no in-flight work means the agent quit with work
    # still to do — re-prompt it. This is the original, unchanged behavior.
    out, _ = run_hook(tmp_path, _build_state(in_flight=[]))
    assert BLOCK_MARKER in out


def test_waiting_on_builders_allows_stop(tmp_path):
    # NEW: BUILD with a builder in flight is a legitimate idle-wait, not an early
    # quit. Allow the stop so the loop doesn't spin a full re-prompt per
    # wait-check; the builder's completion notification re-enters the loop.
    out, code = run_hook(tmp_path, _build_state(in_flight=["bd-a1b2"]))
    assert code == 0
    assert BLOCK_MARKER not in out


def test_inflight_does_not_consume_hard_cap_budget(tmp_path):
    # A wait-allow must not increment the anti-spin .hook-blocks counter — it is
    # not a spin, it is the absence of one.
    run_hook(tmp_path, _build_state(in_flight=["bd-a1b2"]), hook_blocks=5)
    counter = (tmp_path / ".sdlc" / ".hook-blocks").read_text().strip()
    assert counter == "5"


def test_current_task_fallback_counts_as_inflight(tmp_path):
    # Pre-2.1 loops used a single `current_task` slot instead of `in_flight`.
    state = {"state": "BUILD", "driver": "auto", "current_task": "bd-old"}
    out, code = run_hook(tmp_path, state)
    assert code == 0
    assert BLOCK_MARKER not in out


def test_non_build_state_with_inflight_still_blocks(tmp_path):
    # Conservative scope: the wait-allow is BUILD-only. An unexpected in-flight
    # set in another active state must NOT silently release the loop.
    out, _ = run_hook(tmp_path, _build_state(state="VERIFY", in_flight=["bd-x"]))
    assert BLOCK_MARKER in out


def test_terminal_states_release_even_with_inflight(tmp_path):
    for terminal in ("DONE", "BLOCKED"):
        out, code = run_hook(
            tmp_path, _build_state(state=terminal, in_flight=["bd-x"])
        )
        assert code == 0
        assert BLOCK_MARKER not in out, terminal


def test_driver_goal_stands_hook_down(tmp_path):
    # When the user has armed /goal, the Stop hook must not also drive.
    out, code = run_hook(tmp_path, _build_state(driver="goal"))
    assert code == 0
    assert BLOCK_MARKER not in out


def test_hard_cap_fires_after_200_blocks(tmp_path):
    # The belt-and-braces cap still releases a loop that keeps stopping without
    # ever ticking (in_flight empty, so it is a real spin, not a wait).
    out, code = run_hook(tmp_path, _build_state(in_flight=[]), hook_blocks=200)
    assert code == 0
    assert "hard cap" in out.lower()


if __name__ == "__main__":
    # Minimal fallback runner so the suite works without pytest installed.
    import tempfile
    import traceback

    tests = [
        test_no_state_file_is_noop,
        test_build_without_inflight_blocks,
        test_waiting_on_builders_allows_stop,
        test_inflight_does_not_consume_hard_cap_budget,
        test_current_task_fallback_counts_as_inflight,
        test_non_build_state_with_inflight_still_blocks,
        test_terminal_states_release_even_with_inflight,
        test_driver_goal_stands_hook_down,
        test_hard_cap_fires_after_200_blocks,
    ]
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
