#!/bin/bash
# ABOUTME: Permission hook for autonomous SDLC loops: approve routine work, hard-deny the denylist.
# ABOUTME: Replaces v1 auto-approve-all.sh — an unattended loop needs rails, not blanket approval.

INPUT=$(cat)

# No active loop → defer to the user's normal permission flow.
if [ ! -f ".sdlc/state.json" ] && [ ! -d ".sdlc" ]; then
    echo '{}'
    exit 0
fi

python3 - "$INPUT" <<'PYEOF'
# Denylist: operations an unattended loop must never perform. Denied with a
# reason so the agent can pick a safe alternative and keep the loop moving.
import json
import re
import sys

event = json.loads(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] else {}
tool = event.get("tool_name", "")
cmd = ""
if tool == "Bash":
    cmd = event.get("tool_input", {}).get("command", "")

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
        print(json.dumps({
            "decision": "deny",
            "reason": f"SDLC loop denylist: {label} is not allowed inside an "
                      f"autonomous loop. Stay on the feature branch; if this is "
                      f"truly required, escalate (transition BLOCKED) instead.",
        }))
        sys.exit(0)

print(json.dumps({"decision": "allow"}))
PYEOF
