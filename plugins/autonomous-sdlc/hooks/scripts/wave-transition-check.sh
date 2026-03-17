#!/bin/bash
# ABOUTME: Hook handler for TaskCompleted and TeammateIdle events in autonomous SDLC
# ABOUTME: Surfaces agent lifecycle events so the lead can decide on wave transitions

# Read the JSON event payload from stdin
EVENT_JSON=$(cat)

# Extract key fields from the event payload
AGENT_ID=$(echo "$EVENT_JSON" | grep -o '"agent_id":"[^"]*"' | cut -d'"' -f4)
HOOK_EVENT=$(echo "$EVENT_JSON" | grep -o '"hook_event_name":"[^"]*"' | cut -d'"' -f4)
TRANSCRIPT_PATH=$(echo "$EVENT_JSON" | grep -o '"agent_transcript_path":"[^"]*"' | cut -d'"' -f4)

# Log the event for observability
TIMESTAMP=$(date -Iseconds)
LOG_DIR=".sdlc/events"

if [ -d ".sdlc" ]; then
    mkdir -p "$LOG_DIR"
    echo "{\"timestamp\":\"$TIMESTAMP\",\"hook_event\":\"$HOOK_EVENT\",\"agent_id\":\"$AGENT_ID\",\"transcript_path\":\"$TRANSCRIPT_PATH\"}" >> "$LOG_DIR/hook-events.jsonl"
fi

# Surface the event to the lead — include full payload for context
# The lead decides whether to assign more work (TeammateIdle) or advance the wave (TaskCompleted)
echo "{\"message\": \"[$HOOK_EVENT] agent=$AGENT_ID timestamp=$TIMESTAMP — lead should assess wave transition\", \"event\": $EVENT_JSON}"
