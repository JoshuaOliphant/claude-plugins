#!/bin/bash
# ABOUTME: PreToolUse rail for autonomous SDLC loops: denies the destructive-command denylist.
# ABOUTME: PreToolUse runs before permission checks in every mode, so this binds even under bypassPermissions.

INPUT=$(cat)

python3 - "$INPUT" <<'PYEOF'
# Active loop (state.json exists, state not terminal) → deny the denylist with a
# reason so the agent picks a safe alternative. Anything else (no loop, finished
# loop, unreadable input, not a Bash call) → no output, which lets the normal
# permission flow decide.
#
# The full command string is regex-matched here rather than narrowed with the
# hook `if` field: `if` cannot carry alternation, so ten patterns would mean ten
# handlers, and one small script is easier to test (see test_hooks.py).
import json
import re
import sys


def defer():
    sys.exit(0)


try:
    state = json.load(open(".sdlc/state.json"))
except (OSError, ValueError):
    defer()
if state.get("state") in ("DONE", "BLOCKED"):
    defer()

try:
    event = json.loads(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] else {}
except ValueError:
    defer()

if event.get("tool_name") != "Bash":
    defer()
cmd = event.get("tool_input", {}).get("command", "") or ""

DENY = [
    (r"push\s+.*(--force|-f\b)", "force-push"),
    (r"git\s+push\s+\S*\s*(origin\s+)?(main|master)\b", "push to main/master"),
    (r"git\s+branch\s+-D\s+(main|master)\b", "delete main/master"),
    (r"git\s+reset\s+--hard\s+origin", "hard reset to remote"),
    (r"rm\s+(-\w*r\w*f|\-\w*f\w*r)\w*\s+[/~]", "recursive delete outside the worktree"),
    (r"\b(npm|pnpm|yarn)\s+publish\b", "package publish"),
    (r"\btwine\s+upload\b", "package publish"),
    (r"\bcargo\s+publish\b", "package publish"),
    (r"\bgh\s+repo\s+delete\b", "repository deletion"),
    (r"\bgit\s+push\s+--delete\b", "remote branch deletion"),
]

for pattern, label in DENY:
    if cmd and re.search(pattern, cmd):
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": (
                            f"SDLC loop denylist: {label} is not allowed inside an "
                            f"autonomous loop. Stay on the feature branch; if this is "
                            f"truly required, escalate (transition BLOCKED) instead."
                        ),
                    }
                }
            )
        )
        sys.exit(0)
PYEOF
