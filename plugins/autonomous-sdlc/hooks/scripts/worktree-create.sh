#!/bin/bash
# ABOUTME: WorktreeCreate hook for autonomous SDLC workflows
# ABOUTME: Logs worktree creation events; declines non-git delegation it cannot honestly serve

# Contract (https://code.claude.com/docs/en/hooks.md): stdout is reserved for the
# absolute path of a worktree this hook CREATED — the harness chdirs to the first
# non-empty line. Inside a git repo, native git worktrees handle isolation and this
# hook only observes, so it must emit nothing on stdout. Outside a git repo the
# harness delegates creation to this hook; there is no VCS here to produce a real
# isolated copy from, so fail cleanly instead of returning a path that would
# silently break isolation.

EVENT_JSON=$(cat)
WORKTREE_NAME=$(echo "$EVENT_JSON" | grep -o '"worktree_name":"[^"]*"' | cut -d'"' -f4)
BASE_REF=$(echo "$EVENT_JSON" | grep -o '"base_ref":"[^"]*"' | cut -d'"' -f4)
TIMESTAMP=$(date -Iseconds)

if [ -d ".sdlc" ]; then
    LOG_DIR=".sdlc/events"
    mkdir -p "$LOG_DIR"
    echo "{\"timestamp\":\"$TIMESTAMP\",\"hook_event\":\"WorktreeCreate\",\"worktree_name\":\"$WORKTREE_NAME\",\"base_ref\":\"$BASE_REF\"}" >> "$LOG_DIR/hook-events.jsonl"
fi

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    exit 0
fi

echo "[WorktreeCreate] $PWD is not a git repository; cannot create a VCS-backed worktree here. Run worktree isolation inside the target git repo instead." >&2
exit 1
