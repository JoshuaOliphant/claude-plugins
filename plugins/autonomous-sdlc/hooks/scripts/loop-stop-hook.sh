#!/bin/bash
# ABOUTME: Fallback outer-loop driver for Claude Code without /goal (< v2.1.139).
# ABOUTME: Blocks session stop and re-injects the iteration ritual until the state machine says DONE or BLOCKED.

[ -f ".sdlc/state.json" ] || exit 0

# Resolve the plugin root from this script's own location so messages carry a
# real path, not an unexpanded ${CLAUDE_PLUGIN_ROOT} the model can't resolve.
PLUGIN_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
STATE_CLI="$PLUGIN_ROOT/scripts/sdlc_state.py"

# One read: drive the loop unless the native /goal driver owns it. "auto" means
# /sdlc hasn't recorded a successful /goal arm (set-driver goal) yet, so the
# fallback must drive — otherwise a failed probe would leave no driver at all.
read -r DRIVER STATE <<<"$(python3 -c "
import json
s = json.load(open('.sdlc/state.json'))
print(s.get('driver', ''), s.get('state', ''))
" 2>/dev/null)"

case "$DRIVER" in
    stop-hook|auto) ;;
    *) exit 0 ;;
esac

# Terminal states release the loop.
if [ -z "$STATE" ] || [ "$STATE" = "DONE" ] || [ "$STATE" = "BLOCKED" ]; then
    rm -f .sdlc/.hook-blocks
    echo '{}'
    exit 0
fi

# Belt-and-braces cap, independent of the in-state budgets: if the model keeps
# stopping without ever ticking (which would trip the budgets), release anyway.
BLOCKS=$(( $(cat .sdlc/.hook-blocks 2>/dev/null || echo 0) + 1 ))
echo "$BLOCKS" > .sdlc/.hook-blocks
if [ "$BLOCKS" -gt 200 ]; then
    echo "{\"decision\": \"block\", \"reason\": \"Loop hard cap reached (200 re-entries). Run: python3 $STATE_CLI transition BLOCKED --reason 'hook hard cap' — then stop.\"}"
    exit 0
fi

cat <<EOF
{"decision": "block", "reason": "SDLC loop is in state $STATE — it is not finished. Run the next iteration per the sdlc-loop skill: (1) python3 $STATE_CLI tick, (2) orient from .sdlc/progress.md, .sdlc/signs.md and git log, (3) do ONE unit of work for $STATE, (4) commit and record a transition or note-progress, (5) stop. If tick prints DONE or BLOCKED, just stop."}
EOF
