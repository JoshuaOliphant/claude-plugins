#!/usr/bin/env bash
# Observability stack installer — downloads Vector (always) and, in full mode,
# VictoriaLogs + VictoriaMetrics. Idempotent: skips download if correct version present.
# Mode is read from harness.env (OBS_MODE=lite|full). Supports macOS/Linux on amd64/arm64.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR/bin"

# shellcheck disable=SC1091
[ -f "$SCRIPT_DIR/harness.env" ] && source "$SCRIPT_DIR/harness.env"
OBS_MODE="${OBS_MODE:-lite}"

# Pinned versions for reproducibility
VECTOR_VERSION="v0.55.0"
VM_VERSION="v1.139.0"
VL_VERSION="v1.24.0-victorialogs"

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
RAW_ARCH="$(uname -m)"
case "$RAW_ARCH" in
    x86_64)  ARCH="amd64" ;;
    arm64)   ARCH="arm64" ;;
    aarch64) ARCH="arm64" ;;
    *)       echo "ERROR: Unsupported architecture: $RAW_ARCH" >&2; exit 1 ;;
esac

echo "Platform: ${OS}/${ARCH}  Mode: ${OBS_MODE}"
mkdir -p "$BIN_DIR"

download_vector() {
    local binary="$BIN_DIR/vector"
    if [ -f "$binary" ] && "$binary" --version 2>&1 | grep -q "${VECTOR_VERSION#v}"; then
        echo "Vector ${VECTOR_VERSION} already installed"; return 0
    fi
    echo "Downloading Vector ${VECTOR_VERSION}..."
    local vector_target
    case "${OS}-${RAW_ARCH}" in
        darwin-arm64)   vector_target="arm64-apple-darwin" ;;
        darwin-x86_64)  vector_target="x86_64-apple-darwin" ;;
        linux-x86_64)   vector_target="x86_64-unknown-linux-gnu" ;;
        linux-aarch64)  vector_target="aarch64-unknown-linux-gnu" ;;
        linux-arm64)    vector_target="aarch64-unknown-linux-gnu" ;;
        *)              echo "ERROR: Unsupported platform for Vector: ${OS}-${RAW_ARCH}" >&2; return 1 ;;
    esac
    local url="https://github.com/vectordotdev/vector/releases/download/${VECTOR_VERSION}/vector-${VECTOR_VERSION#v}-${vector_target}.tar.gz"
    local tmpfile tmpdir
    tmpfile=$(mktemp); tmpdir=$(mktemp -d)
    if ! curl -sfL "$url" -o "$tmpfile"; then
        echo "ERROR: Failed to download Vector from $url" >&2; rm -f "$tmpfile"; return 1
    fi
    tar xz -C "$tmpdir" -f "$tmpfile"; rm -f "$tmpfile"
    mv -f "$tmpdir"/vector-"${vector_target}"/bin/vector "$binary"; rm -rf "$tmpdir"
    chmod +x "$binary"
    echo "Vector ${VECTOR_VERSION}: $("$binary" --version 2>&1 | head -1)"
}

download_victoria_metrics() {
    local binary="$BIN_DIR/victoria-metrics-prod"
    if [ -f "$binary" ] && "$binary" --version 2>&1 | grep -q "${VM_VERSION#v}"; then
        echo "VictoriaMetrics ${VM_VERSION} already installed"; return 0
    fi
    echo "Downloading VictoriaMetrics ${VM_VERSION}..."
    local url="https://github.com/VictoriaMetrics/VictoriaMetrics/releases/download/${VM_VERSION}/victoria-metrics-${OS}-${ARCH}-${VM_VERSION}.tar.gz"
    local tmpfile; tmpfile=$(mktemp)
    if ! curl -sfL "$url" -o "$tmpfile"; then
        echo "ERROR: Failed to download VictoriaMetrics from $url" >&2; rm -f "$tmpfile"; return 1
    fi
    tar xz -C "$BIN_DIR" -f "$tmpfile"; rm -f "$tmpfile"; chmod +x "$binary"
    echo "VictoriaMetrics ${VM_VERSION}: $("$binary" --version 2>&1 | head -1)"
}

download_victoria_logs() {
    local binary="$BIN_DIR/victoria-logs-prod"
    # Match the numeric version (strip leading v and -victorialogs suffix) so a VL_VERSION
    # bump forces a re-download, consistent with the Vector/VictoriaMetrics checks above.
    local vl_num="${VL_VERSION#v}"; vl_num="${vl_num%-victorialogs}"
    if [ -f "$binary" ] && "$binary" --version 2>&1 | grep -q "$vl_num"; then
        echo "VictoriaLogs ${VL_VERSION} already installed"; return 0
    fi
    echo "Downloading VictoriaLogs ${VL_VERSION}..."
    local url="https://github.com/VictoriaMetrics/VictoriaMetrics/releases/download/${VL_VERSION}/victoria-logs-${OS}-${ARCH}-${VL_VERSION}.tar.gz"
    local tmpfile; tmpfile=$(mktemp)
    if ! curl -sfL "$url" -o "$tmpfile"; then
        echo "ERROR: Failed to download VictoriaLogs from $url" >&2; rm -f "$tmpfile"; return 1
    fi
    tar xz -C "$BIN_DIR" -f "$tmpfile"; rm -f "$tmpfile"; chmod +x "$binary"
    echo "VictoriaLogs ${VL_VERSION}: $("$binary" --version 2>&1 | head -1)"
}

echo "=== Observability Stack Installer ==="
download_vector
if [ "$OBS_MODE" = "full" ]; then
    download_victoria_metrics
    download_victoria_logs
fi
echo "=== Binaries installed to $BIN_DIR ==="
