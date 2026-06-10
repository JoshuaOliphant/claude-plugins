#!/usr/bin/env bash
# Verify the telemetry pipeline end-to-end: run the probe, then assert the probe's
# span/metric/log actually landed in the JSONL sinks. Exit 0 only on full success.
# Usage: verify.sh [--py "<python command>"]   (default: "python3"; e.g. --py "uv run python")
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="python3"
[ "${1:-}" = "--py" ] && PY="$2"

PROBE="$SCRIPT_DIR/probe.py"
JSONL="$SCRIPT_DIR/data/jsonl"
DAY=$(date +%F)

if [ ! -f "$PROBE" ]; then
    echo "VERIFY FAIL: $PROBE not found — render assets/probe.py.template during scaffolding" >&2
    exit 1
fi

# Stage 1: transport — the probe asserts configure()==True and force-flushes.
# Run from the project root so the app module ({{MODULE_IMPORT}}) is importable.
( cd "$SCRIPT_DIR/../../.." && $PY "$PROBE" ) || exit 1

# Stage 2: sinks — Vector flushes JSONL on a short interval; poll up to 15s.
check_sink() {
    local kind="$1" needle="$2" file="$JSONL/$kind/$DAY.jsonl"
    for _ in $(seq 1 15); do
        [ -f "$file" ] && grep -qF "$needle" "$file" && return 0
        sleep 1
    done
    echo "VERIFY FAIL: no '$needle' in $file after 15s — transport OK but the $kind sink is dry. Check vector status and logs/." >&2
    return 1
}

check_sink traces  "harness.probe"
check_sink metrics "harness.probe.count"
check_sink logs    "harness probe log line"

echo "VERIFY OK: probe telemetry landed in traces, metrics, and logs sinks ($JSONL/*/$DAY.jsonl)"
echo "Next: exercise the app once and confirm the DOMAIN instruments fire with real labels — synthetic probe success is stage 1 of 2."
