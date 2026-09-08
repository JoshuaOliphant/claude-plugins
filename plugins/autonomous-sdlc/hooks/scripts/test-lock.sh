#!/bin/bash
# ABOUTME: PreToolUse test-lock for fix tasks: denies edits to test files while a fix task is in flight.
# ABOUTME: A green run then proves the bug is gone, not that the test changed (playbook Test stage).

INPUT=$(cat)

python3 - "$INPUT" <<'PYEOF'
# Locked when a task registered with `sdlc-state fix-task <id>` is also in the
# in-flight set. The lead commits the reproducing test BEFORE registering the
# task, so the lock never blocks the test that defines the fix. `task <id>
# --done` lifts it; `fix-task <id> --unlock --reason ...` lifts it early when
# the test itself was wrong (log a decision).
import json
import re
import sys
from pathlib import PurePosixPath


def defer():
    sys.exit(0)


try:
    state = json.load(open(".sdlc/state.json"))
except (OSError, ValueError):
    defer()
if state.get("state") in ("DONE", "BLOCKED"):
    defer()

in_flight = state.get("in_flight") or (
    [state["current_task"]] if state.get("current_task") else []
)
locked = sorted(set(state.get("fix_tasks", [])) & set(in_flight))
if not locked:
    defer()

try:
    event = json.loads(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] else {}
except ValueError:
    defer()
if event.get("tool_name") not in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
    defer()
tool_input = event.get("tool_input", {}) or {}
path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
if not path:
    defer()

TEST_DIRS = {"tests", "test", "spec", "specs", "__tests__", "testing"}
TEST_FILE = re.compile(
    r"(^test_.*\.py$)|(_test\.(py|go|rb|rs|ts|js|tsx|jsx)$)|(\.(test|spec)\.[cm]?[jt]sx?$)"
    r"|(_spec\.rb$)|(Tests?\.(java|kt|cs|swift)$)|(^conftest\.py$)"
)
parts = PurePosixPath(path.replace("\\", "/")).parts
name = parts[-1] if parts else ""
is_test = bool(set(parts[:-1]) & TEST_DIRS) or bool(TEST_FILE.search(name))
if not is_test:
    defer()

print(
    json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"test-lock: fix task {', '.join(locked)} is in flight, so test files "
                    f"are read-only ({path}). Fix the source until the committed reproducing "
                    f"test passes. If the test itself is wrong, the loop lead runs "
                    f"`sdlc-state fix-task <id> --unlock --reason '...'` and logs a decision."
                ),
            }
        }
    )
)
PYEOF
