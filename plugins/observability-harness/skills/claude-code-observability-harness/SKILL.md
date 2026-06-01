---
name: claude-code-observability-harness
description: >-
  Install a local, Docker-free OTLP observability stack (OpenTelemetry → Vector →
  JSONL files, optionally VictoriaLogs + VictoriaMetrics) into a project, and instrument
  the code to emit traces, metrics, and logs. Use this whenever the user wants
  observability, telemetry, tracing, metrics, or structured logging in a project
  during development — phrases like "add observability", "set up OTel", "instrument
  this app", "I want to see traces/metrics locally", "add a telemetry harness", "wire
  up Vector", or "make this app observable". Also use when a Claude Code session would
  benefit from being able to query its own app's telemetry while debugging. Prefer this
  over hand-rolling exporters or reaching for Docker/Jaeger/Grafana — this harness is
  binary-only, auto-starts via a SessionStart hook, and is designed for the agent to
  query telemetry as a feedback signal.
---

# Claude Code Observability Harness

Install a self-contained, container-free telemetry stack into a project's
`.claude/harness/observability/` directory, then instrument the application code so it
emits OpenTelemetry traces, metrics, and logs to that stack. The whole thing runs from
downloaded binaries, auto-starts on session start, and is meant to be **queried by the
agent during development** — telemetry as a feedback loop, not just a dashboard.

This skill is an extraction of two production harnesses (an event-bus library and an
agent web app), so it separates what's universal (the transport plumbing) from what's
project-specific (the domain instruments). The instrumentation step is a *scan-and-propose*,
never a blind copy — different apps need different spans and metrics.

## Architecture

```
app (OTel SDK) ──OTLP/HTTP:4318──▶ Vector ──▶ JSONL files          (always)
                                         ├──▶ VictoriaLogs :9428    (full mode)
                                         └──▶ VictoriaMetrics :8428 (full mode)
```

## Two modes — pick one before scaffolding

| | **lite** | **full** |
|---|---|---|
| Binaries | Vector only (~40 MB) | Vector + VictoriaLogs + VictoriaMetrics (~120 MB) |
| Sinks | dated JSONL files | JSONL **+** VictoriaLogs (LogsQL) + VictoriaMetrics (PromQL) |
| Query | `jq` over JSONL | LogsQL / PromQL HTTP APIs + JSONL |
| Best for | quick local insight, small apps, "just let me see traces" | sustained work, dashboards, throughput/rate analysis, larger apps |

Default to **lite** unless the user wants queryable time-series/log search or names
VictoriaLogs/VictoriaMetrics. Lite can be upgraded to full later by re-running install
in full mode and swapping `vector.toml` — say so rather than implying lite is permanent.

## Workflow

Do these in order. Steps 1–2 and 4–5 are mechanical; **step 3 is the judgment call** and
the reason this skill exists.

### 1. Confirm mode and detect the project shape

- Decide lite vs full (above). If unsure, ask the user in one line.
- Find the project root (`git rev-parse --show-toplevel`), the package manager (prefer
  `uv` if `pyproject.toml` exists), and the language. These templates target **Python**;
  for other languages, adapt the OTel SDK calls but keep the Vector/script layer verbatim
  (it is language-agnostic).
- Pick a `SERVICE_NAME` (default: the repo/package name). This becomes the OTel
  `service.name` resource attribute and the log/metric stream label.

### 2. Scaffold the harness files

Copy the bundled `scripts/` and rendered `assets/` into `.claude/harness/observability/`:

- `install.sh`, `start.sh`, `stop.sh`, `status.sh` — copy verbatim (mode-aware via `harness.env`).
- `harness.env` — render from `assets/harness.env.template` with `SERVICE_NAME` and `OBS_MODE`.
- `vector.toml` — for **lite**, copy `scripts/vector.lite.toml` verbatim. For **full**,
  render `scripts/vector.full.toml` (replace `{{SERVICE_NAME}}` — it labels the VictoriaLogs
  streams). Vector does no placeholder substitution itself, so render before copying.
- **Install the OTel SDK** (Python). Without it, the rendered `otel.py` stays in no-op mode
  and emits nothing — silently. Add the packages (an `otel` dependency group keeps them out
  of the production install path):
  ```bash
  uv add --group otel opentelemetry-sdk opentelemetry-exporter-otlp-proto-http
  ```
  Then the app must install that group (`uv sync --group otel`) wherever telemetry is wanted.
- For the Python app: render `assets/otel.py.template` to a real module (replace
  `{{SERVICE_NAME}}` and `{{MODULE_IMPORT}}`, e.g. `app.otel`). See step 3 for where it
  lives and what instruments to add.
- Optionally render `assets/observability.rules.md.template` to `.claude/rules/observability.md`
  so future sessions get query recipes path-scoped to the harness. Substitute all four
  placeholders or raw `{{...}}` will leak into the doc: `{{SERVICE_NAME}}`, `{{OBS_MODE}}`,
  `{{OTEL_MODULE_PATH}}` (e.g. `app/otel.py`), and `{{SINK_SUMMARY}}` (e.g. "dated JSONL files"
  for lite, or "VictoriaLogs + VictoriaMetrics + JSONL" for full).

Then wire the lifecycle (step 4) and gitignore (step 5).

### 3. Instrumentation scan — the core of this skill

**Do not blind-copy instruments.** The two source harnesses instrument completely
different things (an event bus counts produced/consumed events; an agent app times tool
calls and counts tokens). Read `references/instrumentation-scanning.md` and follow it:
scan the codebase, classify candidate sites into the three point-types (tool/boundary
call sites, dispatch/router sites, and LLM/agent result sites), then **present a
structured proposal and wait for confirmation** before editing. Propose `service.name`,
3–6 domain instruments, and the exact files/lines you'd touch. Apply only what the user
confirms — patterns in this project may differ enough that a silent write would be wrong.

The rendered `otel.py` ships with the no-op-when-absent pattern (zero cost when the OTel
SDK isn't installed) and a stdlib-logging→OTLP bridge. Add the confirmed domain
instruments to it, and call `configure()` once at app startup (FastAPI lifespan, CLI
entrypoint, or `__main__`).

### 4. Wire the SessionStart hook

Add to `.claude/settings.json` so the stack auto-starts each session (idempotent):

```json
{
  "hooks": {
    "SessionStart": [
      { "matcher": "startup",
        "hooks": [{ "type": "command",
          "command": "bash .claude/harness/observability/start.sh" }] } ]
  }
}
```

Merge into any existing `hooks.SessionStart` array rather than overwriting it.

### 5. Gitignore the runtime artifacts

The harness generates binaries, PIDs, logs, and telemetry data — none belong in git.
Add (or confirm) these entries, using directory-level globs so nested files (e.g.
`data/jsonl/**/*.jsonl`) are covered — a known trap is `data/*.json` silently missing
nested paths:

```gitignore
.claude/harness/observability/bin/
.claude/harness/observability/pids/
.claude/harness/observability/logs/
.claude/harness/observability/data/
```

### 6. Verify end-to-end (do not skip — empty data dirs are the #1 false "done")

Running the stack proves nothing until telemetry actually lands. Verify in two cheap stages:

1. **Transport**: a tiny probe that calls the app's `configure()` and emits one span +
   the instruments, force-flushes, then confirm dated JSONL files appear under
   `data/jsonl/{traces,metrics,logs}/`. **First assert `configure()` returned `True`** — a
   `False` means the OTel SDK isn't installed (step 2) and everything is silently no-op, which
   is the real cause behind most "empty dirs" before you reach for the gotcha below. (Logs only
   appear if the log bridge is wired *and* the root logger level permits the record.)
2. **Real call sites**: exercise the app once (one request / one CLI run) and confirm the
   *domain* instruments fired with real labels (e.g. `tool.latency{tool=...}`), not just
   the probe's synthetic ones.

Delete the probe afterward. In full mode, also confirm VictoriaLogs/VictoriaMetrics
ingested via the query recipes in `references/querying.md`.

## Gotchas (learned the hard way)

- **Logging bridge has two gates.** A `LoggingHandler` set to INFO still captures nothing
  if the **root logger** is left at its `WARNING` default — records are filtered before
  reaching the handler. `configure()` must lower the root level (the template does). Symptom:
  traces and metrics flow but the logs sink stays empty.
- **CWD matters for relative sink paths.** `vector.toml` writes to relative `data/jsonl/...`
  paths; `start.sh` cds to the harness dir so they resolve. Don't run Vector from elsewhere.
- **`from otel import tracer` captures a stale no-op.** Import the module and access
  `otel.tracer` / `otel.meter` as attributes, so callers pick up the real providers after
  `configure()` reassigns them. The template documents this.
- **Empty data dirs ≠ broken pipeline.** Two common benign causes, check in this order:
  (1) the OTel SDK isn't installed, so `configure()` returned `False` and everything no-ops
  silently — assert `configure()==True`; (2) the app simply hasn't been exercised since
  instrumentation. Verify (step 6) before concluding the transport is broken.
- **Don't overwrite an existing harness.** If the target already has
  `.claude/harness/observability/`, inspect it first — it may be more advanced than this
  template. Surface the diff; never clobber.

## Bundled resources

- `scripts/` — the stack: `install.sh`, `start.sh`, `stop.sh`, `status.sh`, and both
  `vector.*.toml` variants. Language-agnostic; copy verbatim.
- `assets/otel.py.template` — Python OTel module: no-op-when-absent, log bridge,
  `{{SERVICE_NAME}}` and a marked block for domain instruments.
- `assets/harness.env.template` — per-project `SERVICE_NAME` / `OBS_MODE`.
- `assets/observability.rules.md.template` — path-scoped query recipes for future sessions.
- `references/instrumentation-scanning.md` — **read before step 3.** Detection signals
  for the three instrumentation point-types and the propose-then-apply workflow.
- `references/querying.md` — LogsQL/PromQL recipes (full mode) and `jq`-over-JSONL recipes
  (lite mode), plus real-time Monitor patterns.

## Provenance

Extracted from two production harnesses — a full-stack event-bus library (VictoriaLogs +
VictoriaMetrics + transforms + buffers) and a lightweight agent web app (JSONL-only with a
stdlib-logging→OTLP bridge). The `lite` and `full` modes are those two real variants, so both
are battle-tested rather than speculative; the gotchas above are bugs that actually bit.
