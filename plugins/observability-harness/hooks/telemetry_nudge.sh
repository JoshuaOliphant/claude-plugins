#!/usr/bin/env bash
# ABOUTME: SessionStart hook: when the project has the observability harness, prints one line of context saying
# ABOUTME: whether it is running and to query its telemetry. Reads the harness's files and never executes them.
set -uo pipefail

HARNESS="${CLAUDE_PROJECT_DIR:-$PWD}/.claude/harness/observability"
[ -f "$HARNESS/status.sh" ] || exit 0

# Plugin hooks run in every project, including untrusted clones, so harness.env is parsed, not
# sourced, and only plain names reach the agent's context.
setting() {
    local value=""
    [ -f "$HARNESS/harness.env" ] && value=$(sed -n "s/^$1=[\"']\{0,1\}\([A-Za-z0-9._-]*\).*/\1/p" "$HARNESS/harness.env" | tail -1)
    printf '%s' "${value:-$2}"
}
mode=$(setting OBS_MODE lite)
service=$(setting SERVICE_NAME unknown)

vector_running() {
    local pid
    [ -f "$HARNESS/pids/vector.pid" ] || return 1
    pid=$(tr -cd '0-9' < "$HARNESS/pids/vector.pid")
    [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && [[ "$(ps -p "$pid" -o comm= 2>/dev/null)" == *vector* ]]
}

if vector_running; then
    state="is running (${mode} mode, service ${service})"
else
    state="is not running; start it with bash .claude/harness/observability/start.sh"
fi

echo "This project's observability harness ${state}. Query its traces, logs, and metrics while debugging and when verifying that a change ran (the observability-query skill, and docs/agents/observability.md when present) before adding debug logging."
