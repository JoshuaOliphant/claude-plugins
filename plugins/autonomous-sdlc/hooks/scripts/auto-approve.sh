#!/bin/bash
# ABOUTME: PermissionRequest hook for autonomous SDLC loops: approves routine work while a loop is active.
# ABOUTME: Denies live in deny-destructive.sh (PreToolUse), which binds in every permission mode.

INPUT=$(cat)

python3 - "$INPUT" <<'PYEOF'
# Active loop (state.json exists, state not terminal) → allow, so headless and
# manual-mode sessions never stall on a prompt nobody will answer. Anything else
# (no loop, finished loop, unreadable input) → no output: the user's normal
# permission flow decides. This hook is registered by the sdlc-loop skill's
# frontmatter, so it only exists in sessions that invoked the loop.
import json
import sys


def defer():
    sys.exit(0)


try:
    state = json.load(open(".sdlc/state.json"))
except (OSError, ValueError):
    defer()
if state.get("state") in ("DONE", "BLOCKED"):
    defer()

print(
    json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {"behavior": "allow"},
            }
        }
    )
)
PYEOF
