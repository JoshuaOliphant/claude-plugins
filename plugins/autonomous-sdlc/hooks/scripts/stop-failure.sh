#!/bin/bash
# ABOUTME: StopFailure hook for autonomous SDLC workflows
# ABOUTME: Logs API errors and surfaces them to the lead when SDLC workflow is active

EVENT_JSON=$(cat)
AGENT_ID=$(echo "$EVENT_JSON" | grep -o '"agent_id":"[^"]*"' | cut -d'"' -f4)
STOP_REASON=$(echo "$EVENT_JSON" | grep -o '"stop_reason":"[^"]*"' | cut -d'"' -f4)
TIMESTAMP=$(date -Iseconds)

if [ -d ".sdlc" ]; then
    LOG_DIR=".sdlc/events"
    mkdir -p "$LOG_DIR"
    echo "{\"timestamp\":\"$TIMESTAMP\",\"hook_event\":\"StopFailure\",\"agent_id\":\"$AGENT_ID\",\"stop_reason\":\"$STOP_REASON\"}" >> "$LOG_DIR/hook-events.jsonl"
    echo "{\"systemMessage\": \"[StopFailure] Agent $AGENT_ID stopped due to API error: $STOP_REASON — check rate limits or auth\"}"
else
    exit 0
fi
