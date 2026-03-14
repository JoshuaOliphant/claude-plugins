#!/usr/bin/env bash
# ABOUTME: Template for generating project-specific autoloop runner scripts.
# ABOUTME: The skill fills in placeholders and writes this as auto/run.sh in the target project.
# Autoloop runner — tiered quality gates + structured METRIC output
# This script is IMMUTABLE. The agent must never modify it.
# Exit code 0 = all gates passed, non-zero = broken (agent should revert)
set -euo pipefail

cd "$(dirname "$0")/.."

{QUALITY_GATES}

# ── Final gate: Benchmark / Metric extraction ───────────────────────
echo ""
echo "=== Benchmark ==="
{EXECUTION_COMMAND}

# ── Structured METRIC output ────────────────────────────────────────
echo ""
{METRIC_EXTRACTION_LINES}
