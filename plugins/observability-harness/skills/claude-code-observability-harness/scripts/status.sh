#!/usr/bin/env bash
# Health check for the observability stack — reports UP/DOWN/STALE per service.
# `status.sh --json` is the machine-readable integration contract for other tools
# (e.g. the autonomous-sdlc loop): {"installed","running","mode","service","services"}.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$SCRIPT_DIR/pids"
JSON_MODE=false
[ "${1:-}" = "--json" ] && JSON_MODE=true

# shellcheck disable=SC1091
[ -f "$SCRIPT_DIR/harness.env" ] && source "$SCRIPT_DIR/harness.env"
OBS_MODE="${OBS_MODE:-lite}"
SERVICE_NAME="${SERVICE_NAME:-unknown}"

service_status() {
    local name="$1" health_url="$2" pidfile="$PID_DIR/$1.pid"
    local status="DOWN"
    if [ -f "$pidfile" ]; then
        local pid; pid=$(cat "$pidfile")
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
        fi
    fi
    echo "$status"
}

print_service() {
    local name="$1" port="$2" status="$3" pidfile="$PID_DIR/$1.pid"
    local pid="-"
    [ -f "$pidfile" ] && pid=$(cat "$pidfile")
    printf "  %-18s %-9s PID: %-8s :%s\n" "$name" "$status" "$pid" "$port"
}

VECTOR=$(service_status vector "http://127.0.0.1:8686/health")
VLOGS=""
VMETRICS=""
if [ "$OBS_MODE" = "full" ]; then
    VLOGS=$(service_status victoria-logs "http://127.0.0.1:9428/health")
    VMETRICS=$(service_status victoria-metrics "http://127.0.0.1:8428/health")
fi

if $JSON_MODE; then
    RUNNING=false
    if [ "$OBS_MODE" = "full" ]; then
        [ "$VECTOR" = "UP" ] && [ "$VLOGS" = "UP" ] && [ "$VMETRICS" = "UP" ] && RUNNING=true
    else
        [ "$VECTOR" = "UP" ] && RUNNING=true
    fi
    # JSON-escape the one value that comes from user config
    SVC=${SERVICE_NAME//\\/\\\\}
    SVC=${SVC//\"/\\\"}
    SERVICES="\"vector\": \"$VECTOR\""
    [ -n "$VLOGS" ] && SERVICES="$SERVICES, \"victoria-logs\": \"$VLOGS\", \"victoria-metrics\": \"$VMETRICS\""
    echo "{\"installed\": true, \"running\": $RUNNING, \"mode\": \"$OBS_MODE\", \"service\": \"$SVC\", \"services\": {$SERVICES}}"
else
    echo "=== Observability Stack Status (${OBS_MODE}) ==="
    print_service vector 4318 "$VECTOR"
    if [ "$OBS_MODE" = "full" ]; then
        print_service victoria-logs    9428 "$VLOGS"
        print_service victoria-metrics 8428 "$VMETRICS"
    fi
    echo "==================================="
fi
