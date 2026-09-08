# ABOUTME: Tests for the loop's PreToolUse/PermissionRequest hook scripts (deny-destructive, test-lock, auto-approve).
# ABOUTME: Drives the real shipped scripts with a .sdlc/state.json fixture and checks the documented JSON shapes.
"""Run from this directory: `python3 -m pytest test_hooks.py` (or plain
`python3 test_hooks.py` for the bundled fallback runner)."""

import json
import subprocess
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "hooks" / "scripts"
DENY = SCRIPTS / "deny-destructive.sh"
LOCK = SCRIPTS / "test-lock.sh"
ALLOW = SCRIPTS / "auto-approve.sh"


def run_hook(script, tmp_path, state, event):
    if state is not None:
        (tmp_path / ".sdlc").mkdir(exist_ok=True)
        (tmp_path / ".sdlc" / "state.json").write_text(json.dumps(state))
    result = subprocess.run(
        ["bash", str(script)],
        cwd=tmp_path,
        input=json.dumps(event),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout) if result.stdout.strip() else None


def bash(cmd):
    return {"tool_name": "Bash", "tool_input": {"command": cmd}}


def edit(path, tool="Edit"):
    return {"tool_name": tool, "tool_input": {"file_path": path}}


ACTIVE = {"state": "BUILD", "in_flight": ["bd-1"], "fix_tasks": []}


def _deny(out):
    return out and out["hookSpecificOutput"]["permissionDecision"] == "deny"


# --- deny-destructive (PreToolUse, Bash) ---


def test_deny_force_push_with_pretooluse_shape(tmp_path):
    out = run_hook(DENY, tmp_path, ACTIVE, bash("git push --force origin feature/x"))
    assert out["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert _deny(out)
    assert "force-push" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_deny_push_to_main_even_in_a_compound_command(tmp_path):
    out = run_hook(DENY, tmp_path, ACTIVE, bash("cd sub && git push origin main"))
    assert _deny(out)


def test_deny_push_to_main_via_refspec(tmp_path):
    # Every spelling of "the destination is main" must be caught, not just
    # `origin main`; a bypassPermissions Builder is counting on this rail.
    for cmd in (
        "git push origin HEAD:main",
        "git push origin feature/x:main",
        "git push origin refs/heads/main",
        "git push origin HEAD:refs/heads/master",
        "git push origin +main",
        "git push upstream master",
    ):
        assert _deny(run_hook(DENY, tmp_path, ACTIVE, bash(cmd))), cmd


def test_deny_allows_routine_git(tmp_path):
    for cmd in (
        "git push -u origin feature/x",
        "git push origin feature/main-menu",  # branch names containing main
        "git push origin HEAD:feature/my-main",
        "git push origin main-menu",
        "uv run pytest -q",
    ):
        assert run_hook(DENY, tmp_path, ACTIVE, bash(cmd)) is None, cmd


def test_deny_defers_without_an_active_loop(tmp_path):
    assert run_hook(DENY, tmp_path, None, bash("git push --force")) is None
    done = dict(ACTIVE, state="DONE")
    assert run_hook(DENY, tmp_path, done, bash("git push --force")) is None


def test_deny_ignores_non_bash_tools(tmp_path):
    assert run_hook(DENY, tmp_path, ACTIVE, edit("git push --force")) is None


# --- test-lock (PreToolUse, Write|Edit|MultiEdit|NotebookEdit) ---


def test_lock_denies_test_edits_while_fix_task_in_flight(tmp_path):
    state = {"state": "BUILD", "in_flight": ["bd-fix"], "fix_tasks": ["bd-fix"]}
    for path in (
        "tests/test_auth.py",
        "src/pkg/__tests__/auth.test.ts",
        "auth_test.go",
        "spec/models/user_spec.rb",
        "tests/conftest.py",
    ):
        out = run_hook(LOCK, tmp_path, state, edit(path))
        assert _deny(out), path
        assert "bd-fix" in out["hookSpecificOutput"]["permissionDecisionReason"]
    out = run_hook(LOCK, tmp_path, state, edit("tests/test_x.py", tool="Write"))
    assert _deny(out)


def test_lock_allows_source_edits_during_fix_task(tmp_path):
    state = {"state": "BUILD", "in_flight": ["bd-fix"], "fix_tasks": ["bd-fix"]}
    assert run_hook(LOCK, tmp_path, state, edit("src/auth.py")) is None
    assert run_hook(LOCK, tmp_path, state, edit("docs/testing.md")) is None


def test_lock_leaves_playbook_specs_docs_editable(tmp_path):
    # specs/ holds the loop's own intent, spec and plan documents, not a test suite.
    state = {"state": "BUILD", "in_flight": ["bd-fix"], "fix_tasks": ["bd-fix"]}
    for path in (
        "specs/user-auth-intent.md",
        "specs/user-auth-spec.md",
        "specs/user-auth-plan.md",
    ):
        assert run_hook(LOCK, tmp_path, state, edit(path)) is None, path
    # A real test file under specs/ still locks, by filename.
    assert _deny(run_hook(LOCK, tmp_path, state, edit("specs/auth.spec.ts")))


def test_lock_is_off_when_fix_task_registered_but_not_in_flight(tmp_path):
    # VERIFY registers the fix task; until BUILD puts it in flight the lead can
    # still write and commit the reproducing test.
    state = {"state": "VERIFY", "in_flight": [], "fix_tasks": ["bd-fix"]}
    assert run_hook(LOCK, tmp_path, state, edit("tests/test_auth.py")) is None


def test_lock_is_off_for_feature_tasks_and_without_a_loop(tmp_path):
    assert run_hook(LOCK, tmp_path, ACTIVE, edit("tests/test_auth.py")) is None
    assert run_hook(LOCK, tmp_path, None, edit("tests/test_auth.py")) is None


# --- auto-approve (PermissionRequest) ---


def test_auto_approve_allows_with_documented_shape_during_a_loop(tmp_path):
    out = run_hook(ALLOW, tmp_path, ACTIVE, bash("uv run pytest"))
    assert out == {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {"behavior": "allow"},
        }
    }


def test_auto_approve_defers_without_an_active_loop(tmp_path):
    assert run_hook(ALLOW, tmp_path, None, bash("ls")) is None
    assert run_hook(ALLOW, tmp_path, dict(ACTIVE, state="BLOCKED"), bash("ls")) is None


if __name__ == "__main__":
    import tempfile
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
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
