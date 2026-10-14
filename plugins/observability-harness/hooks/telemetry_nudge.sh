#!/usr/bin/env bash
# ABOUTME: SessionStart hook: when the project has the observability harness, prints one line of context saying
# ABOUTME: whether it is running and to query its telemetry while debugging and verifying. Silent otherwise.
set -uo pipefail

HARNESS="${CLAUDE_PROJECT_DIR:-$PWD}/.claude/harness/observability"
[ -f "$HARNESS/status.sh" ] || exit 0

status=$(bash "$HARNESS/status.sh" --json 2>/dev/null)
mode=$(printf '%s' "$status" | sed -n 's/.*"mode": *"\([^"]*\)".*/\1/p')
service=$(printf '%s' "$status" | sed -n 's/.*"service": *"\([^"]*\)".*/\1/p')

if printf '%s' "$status" | grep -q '"running": *true'; then
    state="is running (${mode} mode, service ${service})"
else
    state="is not running; start it with bash .claude/harness/observability/start.sh"
fi

echo "This project's observability harness ${state}. Query its traces, logs, and metrics while debugging and when verifying that a change ran (the observability-query skill, and docs/agents/observability.md when present) before adding debug logging."
