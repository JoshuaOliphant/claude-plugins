#!/usr/bin/env bash
# Graceful shutdown for the observability stack. Stop order: Vector first (flush buffers),
# then VictoriaMetrics, then VictoriaLogs. Verifies each PID belongs to the expected binary
# before killing, so a recycled PID is never killed by mistake.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$SCRIPT_DIR/pids"
GRACE_PERIOD=5

# shellcheck disable=SC1091
[ -f "$SCRIPT_DIR/harness.env" ] && source "$SCRIPT_DIR/harness.env"
OBS_MODE="${OBS_MODE:-lite}"

stop_service() {
    local name="$1" pidfile="$PID_DIR/$1.pid"
    if [ ! -f "$pidfile" ]; then echo "$name: not running (no PID file)"; return 0; fi
    local pid; pid=$(cat "$pidfile")
    if ! kill -0 "$pid" 2>/dev/null; then
        echo "$name: not running (stale PID $pid)"; rm -f "$pidfile"; return 0
    fi
    local cmdname; cmdname=$(ps -p "$pid" -o comm= 2>/dev/null || echo "")
    # Linux `ps comm` truncates to 15 chars (victoria-metrics → victoria-metric)
    if [[ "$cmdname" != *"${name:0:15}"* ]]; then
        echo "$name: PID $pid is not $name — skipping"; rm -f "$pidfile"; return 0
    fi
    echo -n "$name: stopping (PID $pid)... "
    kill -TERM "$pid" 2>/dev/null || true
    local elapsed=0
    while kill -0 "$pid" 2>/dev/null && [ "$elapsed" -lt "$GRACE_PERIOD" ]; do
        sleep 1; elapsed=$((elapsed + 1))
    done
    if kill -0 "$pid" 2>/dev/null; then
        echo -n "force killing... "; kill -KILL "$pid" 2>/dev/null || true; sleep 1
    fi
    rm -f "$pidfile"; echo "stopped"
}

echo "=== Stopping Observability Stack ==="
stop_service vector
if [ "$OBS_MODE" = "full" ]; then
    stop_service victoria-metrics
    stop_service victoria-logs
fi
echo "=== All services stopped ==="
