#!/usr/bin/env bash
# Idempotent startup for the observability stack. PID-guarded — safe to call repeatedly
# (e.g. from the SessionStart hook). In full mode, starts VictoriaLogs + VictoriaMetrics
# before Vector (Vector needs its backends up). In lite mode, starts only Vector.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR/bin"
PID_DIR="$SCRIPT_DIR/pids"
LOG_DIR="$SCRIPT_DIR/logs"
DATA_DIR="$SCRIPT_DIR/data"

# shellcheck disable=SC1091
[ -f "$SCRIPT_DIR/harness.env" ] && source "$SCRIPT_DIR/harness.env"
OBS_MODE="${OBS_MODE:-lite}"

mkdir -p "$PID_DIR" "$LOG_DIR" "$DATA_DIR/vector" \
    "$DATA_DIR/jsonl/logs" "$DATA_DIR/jsonl/traces" "$DATA_DIR/jsonl/metrics"
[ "$OBS_MODE" = "full" ] && mkdir -p "$DATA_DIR/victoria-logs" "$DATA_DIR/victoria-metrics"

# Housekeeping: prune JSONL older than 3 days, truncate service logs over 10MB.
# JSONL (raw dog-food files) rotate faster than the queryable backends (VL/VM run 7d
# retention, set below) — the backends are the system of record, JSONL is for quick local
# inspection, so the shorter window is intentional, not a mismatch.
find "$DATA_DIR/jsonl" -name "*.jsonl" -mtime +3 -delete 2>/dev/null || true
find "$LOG_DIR" -name "*.log" -size +10M -exec truncate -s 0 {} \; 2>/dev/null || true

# Install binaries if missing
need_install=false
[ ! -f "$BIN_DIR/vector" ] && need_install=true
if [ "$OBS_MODE" = "full" ]; then
    { [ ! -f "$BIN_DIR/victoria-logs-prod" ] || [ ! -f "$BIN_DIR/victoria-metrics-prod" ]; } && need_install=true
fi
if [ "$need_install" = true ]; then
    echo "Binaries not found. Running install.sh..."
    bash "$SCRIPT_DIR/install.sh"
fi

is_running() {
    local name="$1" pidfile="$PID_DIR/$1.pid"
    if [ -f "$pidfile" ]; then
        local pid; pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            local cmdname; cmdname=$(ps -p "$pid" -o comm= 2>/dev/null || echo "")
            # Linux `ps comm` truncates to 15 chars (victoria-metrics → victoria-metric)
            [[ "$cmdname" == *"${name:0:15}"* ]] && return 0
            echo "WARNING: PID $pid is not $name (found: $cmdname) — cleaning up" >&2
        fi
        rm -f "$pidfile"
    fi
    return 1
}

wait_for_health() {
    local name="$1" url="$2" max_attempts="${3:-15}"
    for _ in $(seq 1 "$max_attempts"); do
        curl -sf "$url" >/dev/null 2>&1 && return 0
        sleep 1
    done
    echo "WARNING: $name health check failed after ${max_attempts}s ($url)" >&2
    return 1
}

start_service() {
    local name="$1"; shift
    if is_running "$name"; then
        echo "$name: already running (PID $(cat "$PID_DIR/$name.pid"))"; return 0
    fi
    echo -n "$name: starting... "
    "$@" >> "$LOG_DIR/$name.log" 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_DIR/$name.pid"
    sleep 0.5
    if ! kill -0 "$pid" 2>/dev/null; then
        echo "FAILED (check $LOG_DIR/$name.log)" >&2
        rm -f "$PID_DIR/$name.pid"; return 1
    fi
    echo "started (PID $pid)"
}

if [ "$OBS_MODE" = "full" ]; then
    start_service victoria-logs \
        "$BIN_DIR/victoria-logs-prod" \
        -storageDataPath="$DATA_DIR/victoria-logs" -httpListenAddr=:9428 -retentionPeriod=7d
    start_service victoria-metrics \
        "$BIN_DIR/victoria-metrics-prod" \
        -storageDataPath="$DATA_DIR/victoria-metrics" -httpListenAddr=:8428 -retentionPeriod=7d
    # Advisory only: `|| true` keeps these non-fatal under `set -e`. Vector buffers and
    # retries its sinks, so starting it with backends still warming up is correct — a slow
    # backend health check must NOT abort startup before Vector (the OTLP listener) starts.
    wait_for_health "VictoriaLogs" "http://127.0.0.1:9428/health" || true
    wait_for_health "VictoriaMetrics" "http://127.0.0.1:8428/health" || true
fi

# Run Vector from SCRIPT_DIR so relative sink paths in vector.toml resolve
cd "$SCRIPT_DIR"
start_service vector "$BIN_DIR/vector" --config "$SCRIPT_DIR/vector.toml"
cd - >/dev/null

# Vector is the linchpin — verify it actually serves before claiming the stack is up.
# start_service only does a 0.5s liveness check, which a process that dies on a bad config
# or a bound port would survive. Non-fatal so the banner still prints with the warning.
wait_for_health "Vector" "http://127.0.0.1:8686/health" \
    || echo "WARNING: Vector started but :8686/health is not responding — telemetry may not flow" >&2

echo ""
echo "=== Observability Stack (${OBS_MODE}) ==="
echo "Vector OTLP    grpc://127.0.0.1:4317  http://127.0.0.1:4318"
echo "Vector API     http://127.0.0.1:8686"
if [ "$OBS_MODE" = "full" ]; then
    echo "VictoriaLogs   http://127.0.0.1:9428  (LogsQL)"
    echo "VictoriaMetrics http://127.0.0.1:8428  (PromQL)"
fi
echo "JSONL data     $DATA_DIR/jsonl/"
echo "==========================="
