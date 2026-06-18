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
            feature="demo",
            request="do a thing",
            max_iterations=50,
            max_attempts=3,
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


if __name__ == "__main__":
    # Minimal fallback runner so the suite works without pytest installed.
    import tempfile
    import traceback

    tests = [
        test_default_review_config_preserves_current_behavior,
        test_custom_reviewers_are_recorded,
        test_blank_reviewers_falls_back_to_default,
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
