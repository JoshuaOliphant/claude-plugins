# observability-harness

Drop a local, Docker-free telemetry stack into any project and instrument the code so it
emits OpenTelemetry traces, metrics, and logs — then query that telemetry as a development
feedback signal. No containers, no Jaeger/Grafana; just downloaded binaries that auto-start
on session start.

## Skills

- **claude-code-observability-harness** — Scaffolds `.claude/harness/observability/`
  (OpenTelemetry → Vector → sinks), wires a `SessionStart` hook, gitignores runtime
  artifacts, and instruments the app. The instrumentation step is a **scan-and-propose**:
  it classifies candidate sites (boundary/tool calls, dispatch/routing, result/LLM sites),
  proposes domain-appropriate spans and metrics, and waits for confirmation before writing —
  because different apps need different instruments. (Inside an autonomous SDLC loop it
  decides-and-logs instead of asking.) Setup ends with a **scripted end-to-end verify**:
  `verify.sh` runs the rendered probe and polls all three sinks, so "harness installed"
  is an exit code.
- **observability-query** — The consuming half: triggers when debugging, verifying a
  change ran, or doing performance work in a project that has the harness. Detects it
  via the status contract, then reads telemetry instead of guessing.

## Integration contract

`bash .claude/harness/observability/status.sh --json` →
`{"installed", "running", "mode", "service", "services"}` — how any tool (including the
`autonomous-sdlc` loop, which composes with this plugin as a soft dependency) detects a
harness without knowing its internals. File absent → no harness.

## Modes

- **lite** — Vector + dated JSONL files only (~40 MB). Query with `jq`. Best for quick
  local insight and small apps.
- **full** — adds VictoriaLogs (LogsQL) + VictoriaMetrics (PromQL) with Vector transforms
  and buffer backpressure (~120 MB). Best for sustained work, dashboards, and rate/throughput
  analysis.

Lite can be upgraded to full later by re-running install in full mode and swapping
`vector.toml`.

## Requirements

- **`curl`, `tar`, `bash`** — to download and run the pinned binaries (macOS/Linux, amd64/arm64).
- **Python OTel SDK** (for Python apps) — the bundled `otel.py` module is a **no-op when the
  SDK is absent**, so instrumentation costs nothing in production until you opt in. The
  Vector/script layer is language-agnostic; non-Python apps reuse it and supply their own
  OTel SDK calls.

## Ports

`4317` (OTLP gRPC), `4318` (OTLP HTTP), `8686` (Vector API); full mode also `9428`
(VictoriaLogs) and `8428` (VictoriaMetrics).

## What's bundled

`scripts/` (mode-aware `install`/`start`/`stop`/`status` + both `vector.*.toml`),
`assets/` (`otel.py` template, `harness.env`, path-scoped rules template), and `references/`
(instrumentation-scanning guide + LogsQL/PromQL/jq query recipes).
