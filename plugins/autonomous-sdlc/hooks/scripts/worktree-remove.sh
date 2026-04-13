#!/bin/bash
# ABOUTME: WorktreeRemove hook for autonomous SDLC workflows
# ABOUTME: Logs worktree cleanup events for audit trail

EVENT_JSON=$(cat)
WORKTREE_PATH=$(echo "$EVENT_JSON" | grep -o '"worktree_path":"[^"]*"' | cut -d'"' -f4)
BRANCH=$(echo "$EVENT_JSON" | grep -o '"branch":"[^"]*"' | cut -d'"' -f4)
TIMESTAMP=$(date -Iseconds)

if [ -d ".sdlc" ]; then
    LOG_DIR=".sdlc/events"
    mkdir -p "$LOG_DIR"
    echo "{\"timestamp\":\"$TIMESTAMP\",\"hook_event\":\"WorktreeRemove\",\"worktree_path\":\"$WORKTREE_PATH\",\"branch\":\"$BRANCH\"}" >> "$LOG_DIR/hook-events.jsonl"
fi

exit 0
