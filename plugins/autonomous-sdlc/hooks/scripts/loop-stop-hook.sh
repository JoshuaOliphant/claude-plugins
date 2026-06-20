#!/bin/bash
# ABOUTME: Fallback outer-loop driver for Claude Code without /goal (< v2.1.139).
# ABOUTME: Blocks session stop and re-injects the iteration ritual until the state machine says DONE or BLOCKED.

[ -f ".sdlc/state.json" ] || exit 0

# Resolve the plugin root from this script's own location so messages carry a
# real path, not an unexpanded ${CLAUDE_PLUGIN_ROOT} the model can't resolve.
PLUGIN_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
STATE_CLI="$PLUGIN_ROOT/scripts/sdlc_state.py"

# One read: driver, state, and how many tasks are in flight. "auto" means
# /sdlc hasn't recorded a successful /goal arm (set-driver goal) yet, so the
# fallback must drive — otherwise a failed probe would leave no driver at all.
# in_flight folds in the pre-2.1 single current_task slot for old loops.
read -r DRIVER STATE INFLIGHT <<<"$(python3 -c "
import json
s = json.load(open('.sdlc/state.json'))
inflight = s.get('in_flight') or ([s['current_task']] if s.get('current_task') else [])
print(s.get('driver', ''), s.get('state', ''), len(inflight))
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

# Waiting on background builders: when BUILD has work in flight, the agent is
# legitimately idle-waiting, not quitting with ready work left. Allow the stop
# and let the builder's completion notification re-enter the loop, instead of
# burning a full re-prompt per wait-check. The model-side default is an in-turn
# blocking wait (see the sdlc-loop skill's "Waiting on builders"); this keeps a
# stop cheap if the agent does hand control back. Scoped to BUILD on purpose —
# any other state with in_flight set is unexpected and should still re-prompt.
# No .hook-blocks increment here: a wait is the absence of a spin, not one.
if [ "$STATE" = "BUILD" ] && [ "${INFLIGHT:-0}" -gt 0 ]; then
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
