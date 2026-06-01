# Querying Telemetry

The point of this harness is that the **agent queries it as a feedback signal** during
development — after running tests, while debugging, during performance work. Recipes below
for both modes.

## Lite mode — `jq` over JSONL

Telemetry lands in dated files under `.claude/harness/observability/data/jsonl/{logs,traces,metrics}/`.

```bash
JSONL=.claude/harness/observability/data/jsonl
DAY=$(date +%F)

# Span names emitted today
jq -r '.name // empty' "$JSONL/traces/$DAY.jsonl" | sort | uniq -c

# Metric names + their app-level (non-resource) labels
jq -c 'select(.name) | {name, tags: (.tags // .attributes | with_entries(select(.key|startswith("resource.")|not)))}' \
  "$JSONL/metrics/$DAY.jsonl" | sort -u

# Log lines that carry trace correlation (emitted inside a span)
jq -c 'select(.trace_id != null) | {sev: .severity_text, msg: (.message // .body), trace_id}' \
  "$JSONL/logs/$DAY.jsonl"

# Latency for one operation (histogram data points)
jq -c 'select(.name=="tool.latency")' "$JSONL/metrics/$DAY.jsonl"
```

JSONL field names vary by Vector version (`message` vs `body`, `tags` vs `attributes`) —
the `//` fallbacks above handle both. If a query returns nothing, inspect one raw line
first: `head -1 "$JSONL/traces/$DAY.jsonl" | jq .`

## Full mode — VictoriaLogs (LogsQL) + VictoriaMetrics (PromQL)

OTel names use dots (`agent.tokens`), which are special in PromQL — always
`--data-urlencode` the query or use `{__name__="..."}` brace matching.

```bash
# --- VictoriaLogs (logs + traces-as-loglines), port 9428 ---

# Recent logs (all streams)
curl -s 'http://127.0.0.1:9428/select/logsql/query?query=*&limit=10' | jq .

# Filter by stream (brace syntax required). Streams: "<service>" and "<service>-traces".
curl -s 'http://127.0.0.1:9428/select/logsql/query' \
  --data-urlencode 'query=_stream:{_stream="<service>"}' --data-urlencode 'limit=20' | jq .

# Search message content, last 5 minutes
curl -s 'http://127.0.0.1:9428/select/logsql/query?query=_msg:error&start=5m&limit=50' | jq .

# --- VictoriaMetrics (PromQL), port 8428 ---
#
# `__name__` is the BARE instrument name (e.g. "tool.latency"), NOT service-prefixed —
# the service lands in a label (from the service.name resource attribute), not the name.
# CAVEAT: `prometheus_remote_write` typically normalizes dots to underscores and may append
# suffixes (a histogram "tool.latency" can surface as tool_latency_bucket/_sum/_count). Don't
# guess the exact spelling — list what's actually stored first (last recipe below), then query.

# What's actually stored (run this FIRST to get exact names + labels)
curl -s 'http://127.0.0.1:8428/api/v1/label/__name__/values' | jq .

# A single metric's current value (use a real name from the list above)
curl -s 'http://127.0.0.1:8428/api/v1/query' \
  --data-urlencode 'query={__name__="tool_latency_count"}' | jq .

# Filter by service via label (not via the metric name)
curl -s 'http://127.0.0.1:8428/api/v1/query' \
  --data-urlencode 'query={__name__="router_messages_total", service_name="<service>"}' | jq .

# Throughput (rate over 5m)
curl -s 'http://127.0.0.1:8428/api/v1/query' \
  --data-urlencode 'query=rate({__name__="router_messages_total"}[5m])' | jq .
```

## Real-time monitoring while working

Stream telemetry with a background poll loop + the Monitor tool — useful to watch a metric
move during a test run or reproduce a bug and confirm the warning appears.

```bash
# Lite: tail today's traces as they're written
tail -f .claude/harness/observability/data/jsonl/traces/$(date +%F).jsonl | jq -c '{name, trace_id}'

# Full: poll a metric every 2s
while true; do
  curl -s 'http://127.0.0.1:8428/api/v1/query' \
    --data-urlencode 'query={__name__="<service>.<metric>"}' \
    | jq -r '.data.result[0].value[1] // "0"'
  sleep 2
done
```

## When to query (workflow guidance)

| Scenario | What to check |
|----------|---------------|
| After running tests | Did the instrumented paths fire? Span names present? Expected counters incremented? |
| Verifying a logging fix | Query logs for the specific message after reproducing the bug |
| Performance work | `rate(...)` of the throughput metric during a benchmark; latency histogram spread |
| Producer/consumer lag | Compare the produced vs consumed counters per topic |
| "Is the pipeline even alive?" | Confirm dated JSONL files exist and grew after exercising the app |
