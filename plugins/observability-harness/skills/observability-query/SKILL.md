---
name: observability-query
description: >-
  Query a project's local observability harness (.claude/harness/observability/) as a
  development feedback signal. Use whenever the project has the harness installed and you
  are: debugging ("why is this failing", "is this code path even running"), verifying a
  change actually executed ("did the new endpoint get hit", "did the counter increment"),
  doing performance work (latency, throughput, rates), or checking logs after reproducing
  a bug. Prefer querying telemetry over printf-debugging or rerunning with extra logging —
  the data is already flowing. Trigger phrases: "check the traces", "query the metrics",
  "what do the logs say", "did X fire", "is telemetry showing anything".
---

# Query the Observability Harness

The harness exists so the **agent can read the app's behavior instead of guessing at
it**. Telemetry is a feedback signal: after tests, during debugging, while verifying.

## 1. Detect the harness and its mode

```bash
bash .claude/harness/observability/status.sh --json
# {"installed": true, "running": true, "mode": "lite|full", "service": "...", "services": {...}}
```

- File absent → no harness; this skill doesn't apply (offer the
  `claude-code-observability-harness` skill to set one up).
- `"running": false` → `bash .claude/harness/observability/start.sh` first.
- `"mode"` decides the query surface below.

If the pipeline itself is in doubt (sinks suspiciously empty), run
`bash .claude/harness/observability/verify.sh --py "uv run python"` before concluding
anything from the absence of data — **no data ≠ no activity** until the probe proves the
transport.

## 2. Query

The full recipe collection lives in
[`../claude-code-observability-harness/references/querying.md`](../claude-code-observability-harness/references/querying.md)
— read it for anything beyond the essentials below.

**Lite mode** — `jq` over dated JSONL:

```bash
JSONL=.claude/harness/observability/data/jsonl
DAY=$(date +%F)

# What span names fired today (cheapest "is it running" check)
jq -r '.name // empty' "$JSONL/traces/$DAY.jsonl" | sort | uniq -c

# Recent error/warning logs
jq -c 'select((.severity_text // "") | test("ERROR|WARN")) | {sev: .severity_text, msg: (.message // .body)}' \
  "$JSONL/logs/$DAY.jsonl" | tail -20

# Did a specific instrument record? (e.g. after exercising a new feature)
jq -c 'select(.name=="<instrument.name>")' "$JSONL/metrics/$DAY.jsonl" | tail -5
```

Field names vary by Vector version (`message` vs `body`) — when a query returns nothing,
inspect one raw line first: `head -1 "$JSONL/traces/$DAY.jsonl" | jq .`

**Full mode** — LogsQL (`:9428`) and PromQL (`:8428`); always list what's actually
stored before guessing metric spellings (dots become underscores, histograms sprout
`_bucket/_sum/_count`):

```bash
curl -s 'http://127.0.0.1:8428/api/v1/label/__name__/values' | jq .
curl -s 'http://127.0.0.1:9428/select/logsql/query?query=_msg:error&start=5m&limit=50' | jq .
```

## 3. Answer the actual question

Map the situation to the check (full table in `querying.md`):

| Situation | Check |
|---|---|
| "Did my change actually run?" | Span names / counter for the touched path, after exercising it once |
| Debugging a failure | Error logs in the failure window; the span around the failing call (trace-correlated logs carry `trace_id`) |
| Verifying new instrumentation | Domain instruments fired with **real labels**, not just the probe's synthetic ones |
| Performance | `rate(...)` during a benchmark (full mode); latency histogram points (either mode) |

Report what the telemetry *shows*, distinguish it from what you *infer*, and say which
window you queried. An empty result after a verified pipeline is itself evidence: the
code path did not execute.
