#!/usr/bin/env bash
# Health check for the observability stack — reports UP/DOWN/STALE per service.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$SCRIPT_DIR/pids"

# shellcheck disable=SC1091
[ -f "$SCRIPT_DIR/harness.env" ] && source "$SCRIPT_DIR/harness.env"
OBS_MODE="${OBS_MODE:-lite}"

check_service() {
    local name="$1" port="$2" health_url="$3" pidfile="$PID_DIR/$1.pid"
    local status="DOWN" pid="-"
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            local cmdname; cmdname=$(ps -p "$pid" -o comm= 2>/dev/null || echo "")
            # Linux `ps comm` truncates to 15 chars (victoria-metrics → victoria-metric)
            if [[ "$cmdname" == *"${name:0:15}"* ]]; then
                if [ -n "$health_url" ] && curl -sf "$health_url" >/dev/null 2>&1; then
                    status="UP"
                elif [ -z "$health_url" ]; then
                    status="UP"
                else
                    status="PID_ONLY"
                fi
            else
                status="STALE"
            fi
        else
            pid="stale"
        fi
    fi
    printf "  %-18s %-9s PID: %-8s :%s\n" "$name" "$status" "$pid" "$port"
}

echo "=== Observability Stack Status (${OBS_MODE}) ==="
check_service vector 4318 "http://127.0.0.1:8686/health"
if [ "$OBS_MODE" = "full" ]; then
    check_service victoria-logs    9428 "http://127.0.0.1:9428/health"
    check_service victoria-metrics 8428 "http://127.0.0.1:8428/health"
fi
echo "==================================="
