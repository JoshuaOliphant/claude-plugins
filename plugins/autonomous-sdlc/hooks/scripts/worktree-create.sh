#!/bin/bash
# ABOUTME: WorktreeCreate hook for autonomous SDLC workflows
# ABOUTME: Logs worktree creation and surfaces path/branch to the lead orchestrator

EVENT_JSON=$(cat)
WORKTREE_PATH=$(echo "$EVENT_JSON" | grep -o '"worktree_path":"[^"]*"' | cut -d'"' -f4)
BRANCH=$(echo "$EVENT_JSON" | grep -o '"branch":"[^"]*"' | cut -d'"' -f4)
TIMESTAMP=$(date -Iseconds)

if [ -d ".sdlc" ]; then
    LOG_DIR=".sdlc/events"
    mkdir -p "$LOG_DIR"
    echo "{\"timestamp\":\"$TIMESTAMP\",\"hook_event\":\"WorktreeCreate\",\"worktree_path\":\"$WORKTREE_PATH\",\"branch\":\"$BRANCH\"}" >> "$LOG_DIR/hook-events.jsonl"
fi

echo "{\"systemMessage\": \"[WorktreeCreate] New worktree: path=$WORKTREE_PATH branch=$BRANCH\"}"
